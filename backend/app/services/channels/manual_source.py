from typing import Any

from app.services.channels.canonical_booking import CanonicalBooking
from app.services.channels.channel_source import ChannelSource


class ManualSource(ChannelSource):
    """Adapter for manager-entered walk-in or phone bookings."""

    source_type = "manual"

    async def normalize(self, raw_payload: dict[str, Any]) -> CanonicalBooking:
        """Map manual booking form data to a CanonicalBooking."""
        return CanonicalBooking(
            source_type=self.source_type,
            source_reference=raw_payload.get("source_reference"),
            property_id=raw_payload.get("property_id"),
            room_type_id=raw_payload.get("room_type_id"),
            guest_id=raw_payload.get("guest_id"),
            guest_name=raw_payload.get("guest_name"),
            guest_email=raw_payload.get("guest_email"),
            check_in=raw_payload.get("check_in"),
            check_out=raw_payload.get("check_out"),
            number_of_guests=raw_payload.get("number_of_guests"),
            gross_amount=raw_payload.get("gross_amount", 0),
            discount_amount=raw_payload.get("discount_amount", 0),
            tax_amount=raw_payload.get("tax_amount", 0),
            total_amount=raw_payload.get("total_amount", 0),
            currency=raw_payload.get("currency", "INR"),
            line_items=raw_payload.get("line_items", []),
            special_requests=raw_payload.get("special_requests"),
            booking_date=raw_payload.get("booking_date"),
            raw_payload=raw_payload,
            metadata={"channel": "manager_manual_entry", "entered_by": raw_payload.get("entered_by")},
        )
