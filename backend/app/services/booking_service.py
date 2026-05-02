import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.add_on import AddOn, AddOnType
from app.models.add_on_capacity import AddOnCapacity
from app.models.booking import BookingStatus
from app.models.package import Package
from app.models.property import Property
from app.models.room_type import RoomType
from app.repositories.booking import BookingRepository
from app.repositories.package import PackageRepository
from app.repositories.property import PropertyRepository
from app.repositories.room_type import RoomTypeRepository
from app.schemas.booking import (
    AddOnSelection,
    AmountBreakdown,
    BookingInitRequest,
    BookingInitResponse,
)
from app.exceptions import BookingConflictError
from app.services.addon_slot_service import AddOnSlotService
from app.services.conflict_service import ConflictService
from app.services.inventory_service import InventoryService
from app.services.payment_service import PaymentService
from app.services.pricing_service import PriceBreakdown, PricingService


class BookingInitService:
    """Service for initializing bookings with inventory holds."""

    HOLD_TTL_MINUTES: int = 10

    def __init__(
        self,
        session: AsyncSession,
        org_id: uuid.UUID,
        redis: Redis | None = None,
    ):
        self.session = session
        self.org_id = org_id
        self.redis = redis
        self.booking_repo = BookingRepository(session, org_id)
        self.property_repo = PropertyRepository(session, org_id)
        self.room_type_repo = RoomTypeRepository(session, org_id)
        self.package_repo = PackageRepository(session, org_id)
        self.pricing_service = PricingService(session)

    async def init_booking(
        self,
        data: BookingInitRequest,
    ) -> BookingInitResponse:
        """Create a pending booking and hold inventory.

        Returns existing booking if idempotency key already used.
        """
        # Check idempotency key via Redis
        if data.idempotency_key and self.redis:
            existing_id = await self.redis.get(
                f"idempotency:{self.org_id}:{data.idempotency_key}"
            )
            if existing_id:
                existing_booking = await self.booking_repo.get(
                    uuid.UUID(existing_id)
                )
                if existing_booking:
                    return await self._to_response(existing_booking)

        # Validate property
        prop = await self.property_repo.get(data.property_id)
        if not prop or prop.is_archived:
            raise ValueError("Property not found")

        # Resolve room type and validate
        if data.item_type == "room":
            room_type = await self.room_type_repo.get(data.item_id)
            if not room_type or not room_type.is_active or room_type.is_archived:
                raise ValueError("Room type not found")
            room_type_id = room_type.id
            dates = self._date_range(data.check_in, data.check_out)
        elif data.item_type == "package":
            package = await self.package_repo.get(data.item_id)
            if not package or not package.is_active or package.is_archived:
                raise ValueError("Package not found")
            # Use first composition's room type for hold
            if not package.compositions:
                raise ValueError("Package has no room compositions")
            room_type_id = package.compositions[0].room_type_id
            dates = self._date_range(data.check_in, data.check_out)
        else:
            raise ValueError(f"Invalid item_type: {data.item_type}")

        # Check availability
        inventory_svc = InventoryService(self.session)
        available = await inventory_svc.check_availability(
            data.property_id, room_type_id, data.check_in, data.check_out
        )
        if available < 1:
            conflict_svc = ConflictService(self.session, self.org_id)
            alternatives = await conflict_svc.find_alternatives(
                property_id=data.property_id,
                check_in=data.check_in,
                check_out=data.check_out,
                guests=data.guests,
                excluded_room_type_id=room_type_id if data.item_type == "room" else None,
                excluded_package_id=data.item_id if data.item_type == "package" else None,
            )
            raise BookingConflictError(
                "Insufficient inventory",
                alternatives=alternatives,
            )

        # Calculate price
        if data.item_type == "room":
            price_breakdown = await self.pricing_service.calculate_room_price(
                room_type_id,
                data.check_in,
                data.check_out,
                rate_plan_code=data.rate_plan_code,
                guests=data.guests,
                promo_code=data.promo_code,
                channel_source=data.channel_source or "direct",
            )
        else:
            price_breakdown = await self.pricing_service.calculate_package_price(
                data.item_id,
                data.check_in,
                data.check_out,
                guests=data.guests,
                promo_code=data.promo_code,
                channel_source=data.channel_source or "direct",
            )

        # Build line items from hold context
        line_items_data: list[dict[str, Any]] = [
            {
                "item_type": data.item_type,
                "item_id": str(data.item_id),
                "quantity": 1,
                "nights": len(dates),
                "unit_price": float(price_breakdown.subtotal / len(dates) if dates else Decimal("0.00")),
                "total_price": float(price_breakdown.subtotal),
            }
        ]

        # Prepare addon items for hold
        addon_items: list[dict[str, Any]] = []
        if data.add_on_selections:
            for sel in data.add_on_selections:
                addon_items.append(
                    {
                        "add_on_id": str(sel.add_on_id),
                        "date": sel.date.isoformat(),
                        "quantity": sel.quantity,
                        "slot_time": sel.slot_time.isoformat() if sel.slot_time else None,
                    }
                )

        # Validate slot selections before creating booking
        if data.add_on_selections:
            for sel in data.add_on_selections:
                addon_stmt = select(AddOn).where(AddOn.id == sel.add_on_id)
                addon_result = await self.session.execute(addon_stmt)
                addon = addon_result.scalar_one_or_none()
                if addon and addon.type == AddOnType.slot and sel.slot_time:
                    inventory_svc = InventoryService(self.session)
                    avail = await inventory_svc.check_addon_availability(
                        sel.add_on_id, sel.date, sel.slot_time, sel.quantity
                    )
                    if avail < sel.quantity:
                        slot_svc = AddOnSlotService(self.session)
                        available_slots = await slot_svc.get_available_slots(
                            sel.add_on_id, sel.date
                        )
                        alternatives = []
                        for slot in available_slots:
                            if slot == sel.slot_time:
                                continue
                            cap_stmt = select(AddOnCapacity).where(
                                AddOnCapacity.add_on_id == sel.add_on_id,
                                AddOnCapacity.date == sel.date,
                                AddOnCapacity.slot_time == slot,
                            )
                            cap_result = await self.session.execute(cap_stmt)
                            cap = cap_result.scalar_one_or_none()
                            alternatives.append(
                                {
                                    "item_type": "add_on_slot",
                                    "item_id": sel.add_on_id,
                                    "item_name": f"{addon.name} at {slot.isoformat()}",
                                    "available_count": cap.available_capacity if cap else 0,
                                    "suggested_price": addon.unit_price,
                                    "currency": "INR",
                                }
                            )
                        raise BookingConflictError(
                            f"Slot {sel.slot_time.isoformat()} for {addon.name} is not available",
                            alternatives=alternatives,
                        )

        # Create booking record
        booking_data = {
            "org_id": self.org_id,
            "booking_type": data.item_type,
            "source_type": data.channel_source or "direct",
            "property_id": data.property_id,
            "guest_id": data.guest_id,
            "check_in": data.check_in,
            "check_out": data.check_out,
            "status": BookingStatus.pending_payment.value,
            "gross_amount": price_breakdown.subtotal,
            "discount_amount": price_breakdown.discount_amount,
            "tax_amount": price_breakdown.tax_amount,
            "total_amount": price_breakdown.total_amount,
            "currency": price_breakdown.currency,
            "idempotency_key": data.idempotency_key,
            "notes": data.notes,
            "line_items": [li.model_dump() if hasattr(li, "model_dump") else li for li in line_items_data],
        }
        booking = await self.booking_repo.create_with_line_items(
            booking_data, line_items_data
        )

        # Hold inventory
        hold_id = await inventory_svc.hold_inventory(
            booking_id=booking.id,
            property_id=data.property_id,
            room_type_id=room_type_id,
            dates=dates,
            add_on_items=addon_items if addon_items else None,
        )

        # Store idempotency key in Redis
        if data.idempotency_key and self.redis:
            ttl_seconds = self.HOLD_TTL_MINUTES * 60
            await self.redis.setex(
                f"idempotency:{self.org_id}:{data.idempotency_key}",
                ttl_seconds,
                str(booking.id),
            )

        return BookingInitResponse(
            booking_id=booking.id,
            hold_id=hold_id,
            hold_expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=self.HOLD_TTL_MINUTES),
            amount_breakdown=AmountBreakdown(
                subtotal=price_breakdown.subtotal,
                discount_amount=price_breakdown.discount_amount,
                taxable_amount=price_breakdown.taxable_amount,
                tax_amount=price_breakdown.tax_amount,
                channel_markup_amount=price_breakdown.channel_markup_amount,
                total_amount=price_breakdown.total_amount,
                currency=price_breakdown.currency,
                breakdown_per_night=price_breakdown.breakdown_per_night,
            ),
        )

    @staticmethod
    def _date_range(check_in: date, check_out: date) -> list[date]:
        return [
            check_in + timedelta(days=i)
            for i in range((check_out - check_in).days)
        ]

    async def _to_response(self, booking: Any) -> BookingInitResponse:
        """Build a response from an existing booking."""
        from app.models.inventory_hold import InventoryHold

        result = await self.session.execute(
            select(InventoryHold).where(
                InventoryHold.booking_id == booking.id,
                InventoryHold.status == "active",
            )
        )
        hold = result.scalar_one_or_none()
        hold_id = str(hold.id) if hold else ""
        hold_expires_at = (
            hold.expires_at if hold else datetime.now(timezone.utc)
        )

        return BookingInitResponse(
            booking_id=booking.id,
            hold_id=hold_id,
            hold_expires_at=hold_expires_at,
            amount_breakdown=AmountBreakdown(
                subtotal=booking.gross_amount,
                discount_amount=booking.discount_amount,
                tax_amount=booking.tax_amount,
                total_amount=booking.total_amount,
                taxable_amount=(booking.gross_amount - booking.discount_amount).quantize(Decimal("0.01")),
                channel_markup_amount=Decimal("0.00"),
                currency=booking.currency or "INR",
                breakdown_per_night=[],
            ),
        )

    async def retry_payment(
        self,
        booking_id: uuid.UUID,
    ) -> BookingInitResponse:
        """Retry payment for a booking that previously failed.

        Validates the booking is in ``payment_failed`` status, checks or
        re-creates the inventory hold, increments the Redis retry counter,
        and creates a fresh Razorpay order.
        """
        booking = await self.booking_repo.get(booking_id)
        if not booking:
            raise ValueError("Booking not found")

        if booking.status == BookingStatus.cancelled.value:
            raise ValueError("Booking is cancelled")
        if booking.status == BookingStatus.completed.value:
            raise ValueError("Booking is already completed")
        if booking.status != BookingStatus.payment_failed.value:
            raise ValueError("Booking must be in payment_failed status to retry")

        # Check retry count in Redis
        retry_count = 0
        if self.redis:
            retry_key = f"retry:{booking_id}"
            retry_count_raw = await self.redis.get(retry_key)
            retry_count = int(retry_count_raw) if retry_count_raw else 0
            if retry_count >= 3:
                raise ValueError("Maximum retry attempts exceeded")

        from app.models.inventory_hold import InventoryHold

        result = await self.session.execute(
            select(InventoryHold)
            .where(InventoryHold.booking_id == booking_id)
            .order_by(InventoryHold.created_at.desc())
        )
        hold = result.scalar_one_or_none()

        room_type_id: uuid.UUID | None = None
        dates: list[date] = []
        addon_items: list[dict] = []

        if hold:
            room_type_id = hold.room_type_id
            dates = hold.dates
            addon_items = hold.add_on_holds or []
        else:
            line_items = booking.line_items or []
            if booking.booking_type == "room":
                room_item = next(
                    (li for li in line_items if li.get("item_type") == "room"), None
                )
                if room_item:
                    room_type_id = uuid.UUID(room_item["item_id"])
            elif booking.booking_type == "package":
                pkg_item = next(
                    (li for li in line_items if li.get("item_type") == "package"), None
                )
                if pkg_item:
                    package = await self.package_repo.get(uuid.UUID(pkg_item["item_id"]))
                    if package and package.compositions:
                        room_type_id = package.compositions[0].room_type_id
            dates = self._date_range(booking.check_in, booking.check_out)

        if not room_type_id:
            raise ValueError("Could not determine room type for re-hold")

        inventory_svc = InventoryService(self.session, self.redis)
        hold_id: str | None = None
        hold_expires_at: datetime | None = None

        if hold and hold.status == "active" and hold.expires_at > datetime.now(timezone.utc):
            hold_id = str(hold.id)
            hold_expires_at = hold.expires_at
        else:
            available = await inventory_svc.check_availability(
                booking.property_id,
                room_type_id,
                booking.check_in,
                booking.check_out,
            )
            if available < 1:
                conflict_svc = ConflictService(self.session, self.org_id)
                alternatives = await conflict_svc.find_alternatives(
                    property_id=booking.property_id,
                    check_in=booking.check_in,
                    check_out=booking.check_out,
                    guests=1,
                )
                raise BookingConflictError(
                    "Insufficient inventory",
                    alternatives=alternatives,
                )

            normalised_addons: list[dict] = []
            if addon_items:
                for item in addon_items:
                    norm = dict(item)
                    for key in ("add_on_id", "date", "slot_time"):
                        val = norm.get(key)
                        if isinstance(val, uuid.UUID):
                            norm[key] = str(val)
                        elif isinstance(val, date):
                            norm[key] = val.isoformat()
                        elif isinstance(val, time):
                            norm[key] = val.isoformat()
                    normalised_addons.append(norm)

            hold_id = await inventory_svc.hold_inventory(
                booking_id=booking.id,
                property_id=booking.property_id,
                room_type_id=room_type_id,
                dates=dates,
                add_on_items=normalised_addons if normalised_addons else None,
            )
            hold_expires_at = datetime.now(timezone.utc) + timedelta(
                minutes=self.HOLD_TTL_MINUTES
            )

        # Transition back to pending_payment so PaymentService accepts it
        await self.booking_repo.update(
            booking, {"status": BookingStatus.pending_payment.value}
        )

        if self.redis:
            retry_key = f"retry:{booking_id}"
            new_count = retry_count + 1
            await self.redis.setex(retry_key, 86400, str(new_count))

        payment_svc = PaymentService(self.session, self.org_id, self.redis)
        await payment_svc.create_order(booking.id)

        return BookingInitResponse(
            booking_id=booking.id,
            hold_id=hold_id,
            hold_expires_at=hold_expires_at or datetime.now(timezone.utc),
            amount_breakdown=AmountBreakdown(
                subtotal=booking.gross_amount,
                discount_amount=booking.discount_amount,
                tax_amount=booking.tax_amount,
                total_amount=booking.total_amount,
                taxable_amount=(booking.gross_amount - booking.discount_amount).quantize(Decimal("0.01")),
                channel_markup_amount=Decimal("0.00"),
                currency=booking.currency or "INR",
                breakdown_per_night=[],
            ),
        )
