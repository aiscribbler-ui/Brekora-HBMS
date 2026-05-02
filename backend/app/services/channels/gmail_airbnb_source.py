from typing import Any

from app.repositories.ota_mapping import OTAMappingRepository
from app.schemas.parsed_booking import ParsedBookingResult
from app.services.channels.canonical_booking import CanonicalBooking
from app.services.channels.channel_source import ChannelSource


class GmailAirbnbSource(ChannelSource):
    """Adapter for Airbnb bookings parsed from Gmail."""

    source_type = "gmail_airbnb"

    async def normalize(self, raw_payload: dict[str, Any]) -> CanonicalBooking:
        """Map an Airbnb ParsedBookingResult dict to a CanonicalBooking.

        Expects ``raw_payload`` to contain:
          - ``parsed_result``: dict representation of a ``ParsedBookingResult``
          - ``db_session`` & ``org_id`` (optional): used to resolve the
            ``listing_id`` -> ``room_type_id`` via ``OTAMapping``.
        """
        parsed = ParsedBookingResult.model_validate(raw_payload.get("parsed_result", {}))

        room_type_id = None
        property_id = None
        db_session = raw_payload.get("db_session")
        org_id = raw_payload.get("org_id")

        if db_session and org_id and parsed.listing_id:
            repo = OTAMappingRepository(db_session, org_id)
            mapping = await repo.get_by_listing(self.source_type, parsed.listing_id)
            if mapping:
                room_type_id = mapping.room_type_id
                property_id = mapping.property_id

        return CanonicalBooking(
            source_type=self.source_type,
            source_reference=parsed.ota_reference_id,
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
            },
        )
