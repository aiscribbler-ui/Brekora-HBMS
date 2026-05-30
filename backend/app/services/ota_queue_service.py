import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking, BookingStatus
from app.models.inventory_hold import InventoryHold
from app.models.parsed_booking import ParsedBookingQueue, ParsedBookingStatus
from app.repositories.booking import BookingRepository
from app.repositories.ota_mapping import OTAMappingRepository
from app.repositories.ota_settings import OTASettingsRepository
from app.repositories.parsed_booking_queue import ParsedBookingQueueRepository
from app.repositories.raw_email import RawEmailRepository
from app.schemas.parsed_booking_queue import (
    ParsedBookingQueueConfirmRequest,
    ParsedBookingQueueEditRequest,
    ParsedBookingQueueRejectRequest,
)
from app.services.inventory_service import InventoryService

logger = logging.getLogger(__name__)


class OTAQueueService:
    """Service for managing the parsed OTA booking review queue."""

    def __init__(self, session: AsyncSession, org_id: uuid.UUID):
        self.session = session
        self.org_id = org_id
        self.queue_repo = ParsedBookingQueueRepository(session, org_id)
        self.booking_repo = BookingRepository(session, org_id)
        self.raw_email_repo = RawEmailRepository(session, org_id)
        self.ota_mapping_repo = OTAMappingRepository(session, org_id)
        self.ota_settings_repo = OTASettingsRepository(session, org_id)
        self.inventory_service = InventoryService(session)

    async def list_pending(
        self,
        *,
        source_type: str | None = None,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        max_confidence: Decimal | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> dict[str, Any]:
        """List parsed bookings with optional filters. Returns paginated dict."""
        from sqlalchemy import func, select
        from sqlalchemy.orm import joinedload

        base_stmt = select(ParsedBookingQueue).options(joinedload(ParsedBookingQueue.raw_email))
        count_stmt = select(func.count(ParsedBookingQueue.id))

        if source_type:
            base_stmt = base_stmt.where(ParsedBookingQueue.source_type == source_type)
            count_stmt = count_stmt.where(ParsedBookingQueue.source_type == source_type)
        if status:
            base_stmt = base_stmt.where(ParsedBookingQueue.status == status)
            count_stmt = count_stmt.where(ParsedBookingQueue.status == status)
        if max_confidence is not None:
            base_stmt = base_stmt.where(ParsedBookingQueue.confidence_score <= max_confidence)
            count_stmt = count_stmt.where(ParsedBookingQueue.confidence_score <= max_confidence)
        if date_from or date_to:
            if date_from:
                base_stmt = base_stmt.where(
                    ParsedBookingQueue.parsed_data["check_in"].astext >= date_from.isoformat()
                )
                count_stmt = count_stmt.where(
                    ParsedBookingQueue.parsed_data["check_in"].astext >= date_from.isoformat()
                )
            if date_to:
                base_stmt = base_stmt.where(
                    ParsedBookingQueue.parsed_data["check_in"].astext <= date_to.isoformat()
                )
                count_stmt = count_stmt.where(
                    ParsedBookingQueue.parsed_data["check_in"].astext <= date_to.isoformat()
                )

        base_stmt = base_stmt.offset(skip).limit(limit)
        base_stmt = self.queue_repo._apply_org_scope(base_stmt)
        count_stmt = self.queue_repo._apply_org_scope(count_stmt)

        result = await self.session.execute(base_stmt)
        items = result.scalars().all()

        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar_one()

        return {"items": items, "total": total}

    async def get_stats(self) -> dict[str, int]:
        """Return counts by status for the current org."""
        from sqlalchemy import func, select

        stmt = (
            select(ParsedBookingQueue.status, func.count(ParsedBookingQueue.id))
            .group_by(ParsedBookingQueue.status)
        )
        stmt = self.queue_repo._apply_org_scope(stmt)
        result = await self.session.execute(stmt)
        counts: dict[str, int] = {"total": 0, "pending": 0, "confirmed": 0, "rejected": 0, "failed": 0}
        for row in result.all():
            counts[row[0]] = row[1]
            counts["total"] += row[1]
        return counts

    async def get_details(self, queue_id: uuid.UUID) -> dict[str, Any] | None:
        """Return parsed booking details along with the linked raw email."""
        item = await self.queue_repo.get(queue_id)
        if not item:
            return None

        raw_email = None
        if item.raw_email_id:
            raw_email = await self.raw_email_repo.get(item.raw_email_id)

        return {
            "parsed_booking": item,
            "raw_email": raw_email,
        }

    async def confirm(
        self,
        queue_id: uuid.UUID,
        confirm_request: ParsedBookingQueueConfirmRequest,
        manager_id: uuid.UUID | None,
    ) -> Booking:
        """Confirm a parsed booking and create an actual Booking record."""
        item = await self.queue_repo.get(queue_id)
        if not item:
            raise ValueError("Parsed booking not found")
        if item.status != ParsedBookingStatus.pending.value:
            raise ValueError(f"Cannot confirm booking with status: {item.status}")

        property_id = confirm_request.property_id
        room_type_id = confirm_request.room_type_id

        # Resolve via OTAMapping if either is missing
        if not property_id or not room_type_id:
            listing_id = None
            if item.parsed_data:
                listing_id = item.parsed_data.get("listing_id")
            if listing_id:
                mapping = await self.ota_mapping_repo.get_by_listing(
                    item.source_type, listing_id
                )
                if mapping:
                    property_id = property_id or mapping.property_id
                    room_type_id = room_type_id or mapping.room_type_id

        if not property_id or not room_type_id:
            raise ValueError("property_id and room_type_id are required (or a valid OTA mapping)")

        parsed = item.parsed_data or {}
        check_in = confirm_request.check_in or (date.fromisoformat(parsed["check_in"]) if parsed.get("check_in") else None)
        check_out = confirm_request.check_out or (date.fromisoformat(parsed["check_out"]) if parsed.get("check_out") else None)
        if not check_in or not check_out:
            raise ValueError("check_in and check_out are required")

        # Validate inventory availability
        available = await self.inventory_service.check_availability(
            property_id, room_type_id, check_in, check_out
        )
        if available <= 0:
            raise ValueError("Insufficient inventory for the requested dates")

        # Build line items
        nights = (check_out - check_in).days
        if nights <= 0:
            nights = 1
        gross_amount = confirm_request.gross_amount or (Decimal(str(parsed["gross_amount"])) if parsed.get("gross_amount") else Decimal("0.00"))
        unit_price = gross_amount / nights if nights > 0 else Decimal("0.00")

        line_items = [
            {
                "item_type": "room",
                "item_id": room_type_id,
                "quantity": 1,
                "unit_price": unit_price,
                "nights": nights,
                "total_price": gross_amount,
            }
        ]

        # Determine source_type string for Booking
        source_type_map = {
            "airbnb": "gmail_airbnb",
            "mmt": "gmail_mmt",
            "goibibo": "gmail_goibibo",
        }
        booking_source_type = source_type_map.get(item.source_type, item.source_type)

        booking_data = {
            "booking_type": "room",
            "source_type": booking_source_type,
            "source_reference": item.ota_reference_id,
            "property_id": property_id,
            "check_in": check_in,
            "check_out": check_out,
            "status": BookingStatus.confirmed.value,
            "gross_amount": gross_amount,
            "discount_amount": Decimal("0.00"),
            "tax_amount": Decimal("0.00"),
            "total_amount": gross_amount,
            "currency": "INR",
            "notes": confirm_request.guest_name or parsed.get("guest_name"),
        }

        booking = await self.booking_repo.create_with_line_items(
            booking_data, line_items=line_items
        )

        # Create committed inventory hold so OTA bookings block availability
        nights = (check_out - check_in).days
        if nights <= 0:
            nights = 1
        occupied_dates = [check_in + timedelta(days=i) for i in range(nights)]
        hold = InventoryHold(
            org_id=self.org_id,
            booking_id=booking.id,
            property_id=property_id,
            room_type_id=room_type_id,
            dates=sorted(set(occupied_dates)),
            status="committed",
            expires_at=datetime.now(timezone.utc),
        )
        self.session.add(hold)
        await self.session.flush()

        # Update queue item
        await self.queue_repo.update(
            item,
            {
                "status": ParsedBookingStatus.confirmed.value,
                "confirmed_booking_id": booking.id,
                "manager_id": manager_id,
            },
        )

        return booking

    async def edit(
        self,
        queue_id: uuid.UUID,
        edit_request: ParsedBookingQueueEditRequest,
    ) -> ParsedBookingQueue:
        """Edit a pending parsed booking before confirmation."""
        item = await self.queue_repo.get(queue_id)
        if not item:
            raise ValueError("Parsed booking not found")
        if item.status != ParsedBookingStatus.pending.value:
            raise ValueError(f"Cannot edit booking with status: {item.status}")

        update_data = edit_request.model_dump(exclude_unset=True)

        # Build merged parsed_data starting from existing or empty
        parsed = dict(item.parsed_data) if item.parsed_data else {}
        if "parsed_data" in update_data:
            parsed.update(update_data.pop("parsed_data"))

        # Also update top-level fields inside parsed_data for consistency
        field_map = {
            "ota_reference_id": "ota_reference_id",
            "guest_name": "guest_name",
            "guest_email": "guest_email",
            "check_in": "check_in",
            "check_out": "check_out",
            "number_of_guests": "number_of_guests",
            "gross_amount": "gross_amount",
            "net_payout": "net_payout",
        }
        for schema_field, data_field in field_map.items():
            if schema_field in update_data:
                value = update_data[schema_field]
                if isinstance(value, date):
                    value = value.isoformat()
                elif isinstance(value, Decimal):
                    value = float(value)
                parsed[data_field] = value
        if parsed:
            update_data["parsed_data"] = parsed

        # Update ota_reference_id at model level too
        if "ota_reference_id" in update_data:
            update_data["ota_reference_id"] = update_data["ota_reference_id"]

        return await self.queue_repo.update(item, update_data)

    async def reject(
        self,
        queue_id: uuid.UUID,
        reject_request: ParsedBookingQueueRejectRequest,
        manager_id: uuid.UUID,
    ) -> ParsedBookingQueue:
        """Reject a parsed booking with a reason."""
        item = await self.queue_repo.get(queue_id)
        if not item:
            raise ValueError("Parsed booking not found")
        if item.status != ParsedBookingStatus.pending.value:
            raise ValueError(f"Cannot reject booking with status: {item.status}")

        return await self.queue_repo.update(
            item,
            {
                "status": ParsedBookingStatus.rejected.value,
                "rejection_reason": reject_request.rejection_reason,
                "manager_id": manager_id,
            },
        )

    async def process_auto_confirm(self, parsed_booking_id: uuid.UUID) -> Booking | None:
        """Auto-confirm a parsed booking if org settings allow it."""
        item = await self.queue_repo.get(parsed_booking_id)
        if not item:
            logger.warning("Auto-confirm: parsed booking %s not found", parsed_booking_id)
            return None

        if item.status != ParsedBookingStatus.pending.value:
            logger.info(
                "Auto-confirm: parsed booking %s status is %s, skipping",
                parsed_booking_id,
                item.status,
            )
            return None

        settings = await self.ota_settings_repo.get_by_ota_source(item.source_type)
        if not settings:
            logger.info(
                "Auto-confirm: no settings for source %s, skipping",
                item.source_type,
            )
            return None

        if not settings.is_active:
            logger.info(
                "Auto-confirm: settings inactive for source %s, skipping",
                item.source_type,
            )
            return None

        if not settings.auto_confirm:
            logger.info(
                "Auto-confirm: disabled for source %s, skipping",
                item.source_type,
            )
            return None

        if item.confidence_score < Decimal(str(settings.min_confidence)):
            logger.info(
                "Auto-confirm: confidence %.3f < %.3f for source %s, skipping",
                item.confidence_score,
                settings.min_confidence,
                item.source_type,
            )
            return None

        listing_id = None
        if item.parsed_data:
            listing_id = item.parsed_data.get("listing_id")

        if listing_id:
            mapping = await self.ota_mapping_repo.get_by_listing(
                item.source_type, listing_id
            )
            if not mapping:
                logger.info(
                    "Auto-confirm: no mapping for listing %s, skipping",
                    listing_id,
                )
                return None
        else:
            logger.info(
                "Auto-confirm: no listing_id in parsed data, skipping"
            )
            return None

        parsed = item.parsed_data or {}
        check_in_str = parsed.get("check_in")
        check_out_str = parsed.get("check_out")

        if not check_in_str or not check_out_str:
            logger.info("Auto-confirm: missing dates, skipping")
            return None

        try:
            check_in = (
                date.fromisoformat(check_in_str)
                if isinstance(check_in_str, str)
                else check_in_str
            )
            check_out = (
                date.fromisoformat(check_out_str)
                if isinstance(check_out_str, str)
                else check_out_str
            )
        except (ValueError, TypeError):
            logger.info("Auto-confirm: invalid dates, skipping")
            return None

        gross_amount = parsed.get("gross_amount")
        if gross_amount is not None:
            gross_amount = Decimal(str(gross_amount))

        confirm_req = ParsedBookingQueueConfirmRequest(
            check_in=check_in,
            check_out=check_out,
            gross_amount=gross_amount,
            guest_name=parsed.get("guest_name"),
        )

        try:
            booking = await self.confirm(parsed_booking_id, confirm_req, manager_id=None)
            logger.info(
                "Auto-confirm: booking %s created from parsed booking %s",
                booking.id,
                parsed_booking_id,
            )
            return booking
        except ValueError as exc:
            logger.warning(
                "Auto-confirm: failed for parsed booking %s: %s",
                parsed_booking_id,
                exc,
            )
            return None
