from typing import Any

from app.repositories.ota_mapping import OTAMappingRepository
from app.schemas.parsed_booking import ParsedBookingResult
from app.services.channels.canonical_booking import CanonicalBooking
from app.services.channels.channel_source import ChannelSource


class GmailGoibiboSource(ChannelSource):
    """Adapter for Goibibo bookings parsed from Gmail."""

    source_type = "gmail_goibibo"

    async def normalize(self, raw_payload: dict[str, Any]) -> CanonicalBooking:
        """Map a Goibibo ParsedBookingResult dict to a CanonicalBooking.

        Expects ``raw_payload`` to contain:
          - ``parsed_result``: dict representation of a ``ParsedBookingResult``
          - ``db_session`` & ``org_id`` (optional): used to resolve the
            composite key ``hotel_id+room_id`` -> ``room_type_id`` via
            ``OTAMapping``.
        """
        parsed = ParsedBookingResult.model_validate(raw_payload.get("parsed_result", {}))

        source_reference = parsed.booking_reference or parsed.ota_reference_id

        # Goibibo uses hotel_id + room_details as composite key
        hotel_id = parsed.hotel_id
        room_id = raw_payload.get("room_id") or parsed.room_details
        listing_id = None
        if hotel_id and room_id:
            listing_id = f"{hotel_id}+{room_id}"

        room_type_id = None
        property_id = None
        db_session = raw_payload.get("db_session")
        org_id = raw_payload.get("org_id")

        if db_session and org_id and listing_id:
            repo = OTAMappingRepository(db_session, org_id)
            mapping = await repo.get_by_listing(self.source_type, listing_id)
            if mapping:
                room_type_id = mapping.room_type_id
                property_id = mapping.property_id

        return CanonicalBooking(
            source_type=self.source_type,
            source_reference=source_reference,
            property_id=property_id,
            room_type_id=room_type_id,
            guest_name=parsed.guest_name,
            guest_email=parsed.guest_email,
            check_in=parsed.check_in,
            check_out=parsed.check_out,
            number_of_guests=parsed.number_of_guests,
            gross_amount=parsed.gross_amount or 0,
            ota_commission=parsed.ota_commission,
            net_payout=parsed.net_payout,
            special_requests=parsed.special_requests,
            booking_date=parsed.booking_date,
            raw_payload=raw_payload,
            metadata={
                "parser_confidence": parsed.overall_confidence,
                "needs_manual_review": parsed.needs_manual_review,
                "review_reason": parsed.review_reason,
                "hotel_id": parsed.hotel_id,
                "room_details": parsed.room_details,
            },
        )
