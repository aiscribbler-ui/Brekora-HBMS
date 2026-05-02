import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import BookingConflictError
from app.models.add_on import AddOn
from app.models.booking import Booking, BookingStatus
from app.models.inventory_hold import InventoryHold
from app.repositories.booking import BookingRepository
from app.repositories.package import PackageRepository
from app.services.conflict_service import ConflictService
from app.services.inventory_service import InventoryService
from app.services.payment_service import PaymentService
from app.services.pricing_service import PricingService


class BookingModificationService:
    """Service for modifying confirmed bookings with repricing and inventory management."""

    def __init__(
        self,
        session: AsyncSession,
        org_id: uuid.UUID,
        redis: Redis | None = None,
        actor_user_id: uuid.UUID | None = None,
    ):
        self.session = session
        self.org_id = org_id
        self.redis = redis
        self.actor_user_id = actor_user_id
        self.booking_repo = BookingRepository(session, org_id)
        self.pricing_service = PricingService(session)
        self.package_repo = PackageRepository(session, org_id)

    @staticmethod
    def _date_range(check_in: date, check_out: date) -> list[date]:
        return [
            check_in + timedelta(days=i)
            for i in range((check_out - check_in).days)
        ]

    async def can_modify(self, booking_id: uuid.UUID) -> bool:
        """Check whether the booking can be modified (outside 24h window)."""
        booking = await self.booking_repo.get(booking_id)
        if not booking:
            return False
        now = datetime.now(timezone.utc)
        check_in_dt = datetime.combine(booking.check_in, time.min, tzinfo=timezone.utc)
        return (check_in_dt - now) > timedelta(hours=24)

    async def modify_booking(
        self,
        booking_id: uuid.UUID,
        modifications: dict[str, Any],
    ) -> dict[str, Any]:
        """Modify a confirmed booking and handle repricing / inventory.

        Returns a dict with keys:
        - booking: the updated Booking ORM instance
        - payment_difference: Decimal (new_total - old_total)
        - new_total: Decimal
        - razorpay_order: dict | None
        - refund_amount: Decimal | None
        """
        booking = await self.booking_repo.get(booking_id)
        if not booking:
            raise ValueError("Booking not found")

        if booking.status != BookingStatus.confirmed.value:
            raise ValueError(
                f"Booking must be confirmed to modify; current status: {booking.status}"
            )

        if not await self.can_modify(booking_id):
            raise ValueError("Modifications are blocked within 24 hours of check-in")

        # Capture old values before mutation (for audit log)
        old_check_in = booking.check_in
        old_check_out = booking.check_out
        old_total = booking.total_amount

        # Extract proposed changes
        new_check_in = modifications.get("check_in") or booking.check_in
        new_check_out = modifications.get("check_out") or booking.check_out
        new_room_type_id = modifications.get("room_type_id")
        add_ons = modifications.get("add_ons")
        guest_details = modifications.get("guest_details")
        reason = modifications.get("reason", "Booking modification")

        # Resolve current room type from line_items JSONB
        current_line_items = booking.line_items or []
        current_room_type_id: uuid.UUID | None = None
        current_package_id: uuid.UUID | None = None

        room_item = next(
            (li for li in current_line_items if li.get("item_type") == "room"), None
        )
        package_item = next(
            (li for li in current_line_items if li.get("item_type") == "package"), None
        )

        if room_item:
            current_room_type_id = uuid.UUID(str(room_item["item_id"]))
        elif package_item:
            current_package_id = uuid.UUID(str(package_item["item_id"]))
            package = await self.package_repo.get(current_package_id)
            if package and package.compositions:
                current_room_type_id = package.compositions[0].room_type_id

        effective_room_type_id = new_room_type_id or current_room_type_id

        dates_changed = new_check_in != old_check_in or new_check_out != old_check_out
        room_type_changed = (
            effective_room_type_id != current_room_type_id
            if current_room_type_id
            else bool(new_room_type_id)
        )

        payment_difference = Decimal("0.00")
        razorpay_order: dict | None = None
        refund_amount: Decimal | None = None
        new_hold_id: str | None = None

        if dates_changed or room_type_changed:
            # Release current inventory hold (active or committed)
            hold_result = await self.session.execute(
                select(InventoryHold).where(
                    InventoryHold.booking_id == booking_id,
                    InventoryHold.status.in_(("active", "committed")),
                )
            )
            current_hold = hold_result.scalar_one_or_none()

            if current_hold:
                inventory_svc = InventoryService(self.session, self.redis)
                await inventory_svc.release_inventory(current_hold.id)

            # Verify new availability
            inventory_svc = InventoryService(self.session, self.redis)
            available = await inventory_svc.check_availability(
                booking.property_id,
                effective_room_type_id,
                new_check_in,
                new_check_out,
            )
            if available < 1:
                conflict_svc = ConflictService(self.session, self.org_id)
                guests = 1
                if guest_details and isinstance(guest_details, dict):
                    guests = guest_details.get("guests", 1)
                alternatives = await conflict_svc.find_alternatives(
                    property_id=booking.property_id,
                    check_in=new_check_in,
                    check_out=new_check_out,
                    guests=guests,
                    excluded_room_type_id=effective_room_type_id
                    if booking.booking_type == "room"
                    else None,
                    excluded_package_id=current_package_id
                    if booking.booking_type == "package"
                    else None,
                )
                raise BookingConflictError(
                    "Insufficient inventory", alternatives=alternatives
                )

            # Re-price
            if booking.booking_type == "room":
                price_breakdown = await self.pricing_service.calculate_room_price(
                    effective_room_type_id,
                    new_check_in,
                    new_check_out,
                    guests=guest_details.get("guests", 1) if guest_details else 1,
                    channel_source="direct",
                )
            else:
                if current_package_id is None:
                    raise ValueError("Cannot determine package for repricing")
                price_breakdown = await self.pricing_service.calculate_package_price(
                    current_package_id,
                    new_check_in,
                    new_check_out,
                    guests=guest_details.get("guests", 1) if guest_details else 1,
                    channel_source="direct",
                )

            # Prepare addon items for hold
            addon_items: list[dict] = []
            if add_ons:
                for sel in add_ons:
                    sel_dict = dict(sel) if hasattr(sel, "dict") else dict(sel)
                    for key in ("add_on_id", "date", "slot_time"):
                        val = sel_dict.get(key)
                        if isinstance(val, uuid.UUID):
                            sel_dict[key] = str(val)
                        elif hasattr(val, "isoformat"):
                            sel_dict[key] = val.isoformat()
                    addon_items.append(sel_dict)

            # Hold new inventory
            dates = self._date_range(new_check_in, new_check_out)
            new_hold_id = await inventory_svc.hold_inventory(
                booking_id=booking.id,
                property_id=booking.property_id,
                room_type_id=effective_room_type_id,
                dates=dates,
                add_on_items=addon_items if addon_items else None,
            )

            # Immediately commit since the booking is already confirmed
            await inventory_svc.commit_inventory(new_hold_id)

            # Update amounts
            new_total = price_breakdown.total_amount
            payment_difference = new_total - old_total

            booking.gross_amount = price_breakdown.subtotal
            booking.discount_amount = price_breakdown.discount_amount
            booking.tax_amount = price_breakdown.tax_amount
            booking.total_amount = price_breakdown.total_amount

            # Update line_items JSONB
            nights = len(dates)
            unit_price = (
                price_breakdown.subtotal / nights if nights > 0 else Decimal("0.00")
            )

            updated_line_items: list[dict] = []
            for li in current_line_items:
                li_copy = dict(li)
                if li_copy.get("item_type") in ("room", "package"):
                    li_copy["nights"] = nights
                    li_copy["unit_price"] = float(unit_price)
                    li_copy["total_price"] = float(price_breakdown.subtotal)
                    if new_room_type_id and li_copy.get("item_type") == "room":
                        li_copy["item_id"] = str(new_room_type_id)
                    updated_line_items.append(li_copy)
                elif li_copy.get("item_type") == "add_on":
                    # drop existing add-ons; they will be re-added below if add_ons provided
                    continue
                else:
                    updated_line_items.append(li_copy)

            # Append add-on line items if provided
            if add_ons:
                for sel in add_ons:
                    sel_dict = dict(sel) if hasattr(sel, "dict") else dict(sel)
                    addon_qty = sel_dict.get("quantity", 1)
                    addon_id = sel_dict.get("add_on_id")
                    addon_unit_price = Decimal("0.00")
                    if addon_id:
                        addon_stmt = select(AddOn).where(
                            AddOn.id == uuid.UUID(str(addon_id))
                        )
                        addon_res = await self.session.execute(addon_stmt)
                        addon = addon_res.scalar_one_or_none()
                        addon_unit_price = addon.unit_price if addon else Decimal("0.00")
                    updated_line_items.append(
                        {
                            "item_type": "add_on",
                            "item_id": str(addon_id) if addon_id else None,
                            "quantity": addon_qty,
                            "unit_price": float(addon_unit_price),
                            "nights": 1,
                            "total_price": float(addon_unit_price * addon_qty),
                        }
                    )

            booking.line_items = updated_line_items
            booking.check_in = new_check_in
            booking.check_out = new_check_out
        else:
            # No date or room type change
            new_total = old_total
            if add_ons:
                updated_line_items = [
                    li for li in current_line_items if li.get("item_type") != "add_on"
                ]
                for sel in add_ons:
                    sel_dict = dict(sel) if hasattr(sel, "dict") else dict(sel)
                    addon_qty = sel_dict.get("quantity", 1)
                    addon_id = sel_dict.get("add_on_id")
                    addon_unit_price = Decimal("0.00")
                    if addon_id:
                        addon_stmt = select(AddOn).where(
                            AddOn.id == uuid.UUID(str(addon_id))
                        )
                        addon_res = await self.session.execute(addon_stmt)
                        addon = addon_res.scalar_one_or_none()
                        addon_unit_price = addon.unit_price if addon else Decimal("0.00")
                    updated_line_items.append(
                        {
                            "item_type": "add_on",
                            "item_id": str(addon_id) if addon_id else None,
                            "quantity": addon_qty,
                            "unit_price": float(addon_unit_price),
                            "nights": 1,
                            "total_price": float(addon_unit_price * addon_qty),
                        }
                    )
                booking.line_items = updated_line_items

        # Build audit entry
        changes: dict[str, Any] = {}
        if new_check_in != old_check_in:
            changes["check_in"] = {
                "old": str(old_check_in),
                "new": str(new_check_in),
            }
        if new_check_out != old_check_out:
            changes["check_out"] = {
                "old": str(old_check_out),
                "new": str(new_check_out),
            }
        if room_type_changed:
            changes["room_type_id"] = {
                "old": str(current_room_type_id) if current_room_type_id else None,
                "new": str(effective_room_type_id) if effective_room_type_id else None,
            }
        if add_ons is not None:
            changes["add_ons"] = {"old": None, "new": add_ons}
        if guest_details is not None:
            changes["guest_details"] = {"old": None, "new": guest_details}

        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor_user_id": str(self.actor_user_id) if self.actor_user_id else None,
            "changes": changes,
            "reason": reason,
        }

        modification_log: list[dict] = []
        if booking.modification_log:
            modification_log = list(booking.modification_log)
        modification_log.append(audit_entry)
        booking.modification_log = modification_log

        # Handle payment difference
        if payment_difference > 0:
            payment_svc = PaymentService(self.session, self.org_id, self.redis)
            razorpay_order = await payment_svc.create_difference_order(
                booking_id, payment_difference
            )
        elif payment_difference < 0:
            refund_amount = abs(payment_difference)
            booking.payment_state = "refund_needed"

        await self.session.flush()
        await self.session.refresh(booking)

        return {
            "booking": booking,
            "payment_difference": payment_difference,
            "new_total": booking.total_amount,
            "razorpay_order": razorpay_order,
            "refund_amount": refund_amount,
        }
