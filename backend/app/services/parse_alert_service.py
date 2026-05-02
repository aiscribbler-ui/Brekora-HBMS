"""Service for managing failed parse alerts and retries."""
import logging
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.parsed_booking import ParsedBookingQueue, ParsedBookingStatus
from app.repositories.parsed_booking_queue import ParsedBookingQueueRepository
from app.repositories.raw_email import RawEmailRepository
from app.services.ota_queue_service import OTAQueueService
from app.services.parsers import PARSER_MAP

logger = logging.getLogger(__name__)


class ParseAlertService:
    """Service for listing, counting, and retrying failed parse alerts."""

    def __init__(self, session: AsyncSession, org_id: uuid.UUID):
        self.session = session
        self.org_id = org_id
        self.queue_repo = ParsedBookingQueueRepository(session, org_id)
        self.raw_email_repo = RawEmailRepository(session, org_id)

    async def list_failed(
        self,
        *,
        source_type: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ParsedBookingQueue]:
        """List failed parse alerts with optional source filter."""
        stmt = select(ParsedBookingQueue).where(
            ParsedBookingQueue.status == ParsedBookingStatus.failed.value
        )
        if source_type:
            stmt = stmt.where(ParsedBookingQueue.source_type == source_type)
        stmt = stmt.offset(skip).limit(limit)
        stmt = self.queue_repo._apply_org_scope(stmt)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_source(self) -> list[dict[str, Any]]:
        """Return count of failed parses grouped by OTA source."""
        stmt = (
            select(ParsedBookingQueue.source_type, func.count(ParsedBookingQueue.id))
            .where(ParsedBookingQueue.status == ParsedBookingStatus.failed.value)
            .group_by(ParsedBookingQueue.source_type)
        )
        stmt = self.queue_repo._apply_org_scope(stmt)
        result = await self.session.execute(stmt)
        return [
            {"source_type": source_type, "count": count}
            for source_type, count in result.all()
        ]

    async def retry(self, queue_id: uuid.UUID) -> ParsedBookingQueue:
        """Retry parsing a raw email linked to a failed alert."""
        item = await self.queue_repo.get(queue_id)
        if not item:
            raise ValueError("Alert not found")

        if item.status != ParsedBookingStatus.failed.value:
            raise ValueError("Can only retry failed alerts")

        if not item.raw_email_id:
            raise ValueError("No raw email linked to this alert")

        raw_email = await self.raw_email_repo.get(item.raw_email_id)
        if not raw_email:
            raise ValueError("Linked raw email not found")

        parser_cls = PARSER_MAP.get(raw_email.ota_source)
        if not parser_cls:
            raise ValueError(f"No parser available for source '{raw_email.ota_source}'")

        parser = parser_cls()
        try:
            parsed_result = parser.parse(raw_email)
        except Exception as exc:
            await self.queue_repo.update(
                item,
                {"review_notes": f"Retry failed: parser_error: {exc}"},
            )
            raise ValueError(f"Parser error on retry: {exc}")

        has_any_fields = (
            parsed_result.ota_reference_id is not None
            or parsed_result.check_in is not None
            or parsed_result.check_out is not None
            or parsed_result.gross_amount is not None
        )
        if not has_any_fields:
            await self.queue_repo.update(
                item,
                {
                    "review_notes": f"Retry failed: missing_fields: {parsed_result.review_reason or 'No critical fields extracted'}"
                },
            )
            raise ValueError("Retry failed: no critical fields extracted")

        parsed_data: dict = {}
        if parsed_result.ota_reference_id:
            parsed_data["ota_reference_id"] = parsed_result.ota_reference_id
        if parsed_result.guest_name:
            parsed_data["guest_name"] = parsed_result.guest_name
        if parsed_result.guest_email:
            parsed_data["guest_email"] = parsed_result.guest_email
        check_in = getattr(parsed_result, "check_in", None)
        if check_in:
            parsed_data["check_in"] = (
                check_in.isoformat() if hasattr(check_in, "isoformat") else str(check_in)
            )
        check_out = getattr(parsed_result, "check_out", None)
        if check_out:
            parsed_data["check_out"] = (
                check_out.isoformat() if hasattr(check_out, "isoformat") else str(check_out)
            )
        listing_id = getattr(parsed_result, "listing_id", None)
        if listing_id:
            parsed_data["listing_id"] = listing_id
        number_of_guests = getattr(parsed_result, "number_of_guests", None)
        if number_of_guests is not None:
            parsed_data["number_of_guests"] = number_of_guests
        gross_amount = getattr(parsed_result, "gross_amount", None)
        if gross_amount is not None:
            parsed_data["gross_amount"] = float(gross_amount)
        net_payout = getattr(parsed_result, "net_payout", None)
        if net_payout is not None:
            parsed_data["net_payout"] = float(net_payout)

        raw_payload = getattr(parsed_result, "raw_payload", None)
        if raw_payload:
            parsed_data.update(raw_payload)

        overall_confidence = getattr(parsed_result, "overall_confidence", 0.0)

        updated = await self.queue_repo.update(
            item,
            {
                "source_type": raw_email.ota_source,
                "ota_reference_id": parsed_result.ota_reference_id,
                "parsed_data": parsed_data,
                "confidence_score": Decimal(str(overall_confidence)),
                "status": ParsedBookingStatus.pending.value,
                "review_notes": None,
            },
        )

        queue_svc = OTAQueueService(self.session, self.org_id)
        await queue_svc.process_auto_confirm(updated.id)

        return updated
