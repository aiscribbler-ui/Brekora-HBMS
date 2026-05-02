from typing import Any

from app.repositories.ota_mapping import OTAMappingRepository
from app.services.channels.canonical_booking import CanonicalBooking
from app.services.channels.channel_source import ChannelSource
from app.services.ical_service import IcalService


class ICalSource(ChannelSource):
    """Adapter for iCal feed ingest (Airbnb iCal, Booking.com iCal, etc.)."""

    source_type = "ical"

    async def normalize(self, raw_payload: dict[str, Any]) -> CanonicalBooking:
        """Map a parsed iCal event dict to a CanonicalBooking.

        If ``raw_payload`` contains a ``feed_url``, the feed is fetched and
        parsed, and the event matching ``uid`` (if provided) is used to
        populate canonical fields.  OTAMapping is resolved when
        ``db_session`` + ``org_id`` + ``listing_id`` are present.
        """
        feed_url = raw_payload.get("feed_url")
        event_data = raw_payload

        if feed_url:
            try:
                events = await IcalService.fetch_and_parse(feed_url)
                events = IcalService.dedup(events)
                target_uid = raw_payload.get("uid")
                if target_uid:
                    for event in events:
                        if event.get("uid") == target_uid:
                            event_data = event
                            break
            except Exception:
                # On fetch/parse error, fall back to raw_payload fields
                pass

        room_type_id = raw_payload.get("room_type_id")
        property_id = raw_payload.get("property_id")
        db_session = raw_payload.get("db_session")
        org_id = raw_payload.get("org_id")
        listing_id = raw_payload.get("listing_id")

        if db_session and org_id and listing_id:
            repo = OTAMappingRepository(db_session, org_id)
            mapping = await repo.get_by_listing(self.source_type, listing_id)
            if mapping:
                room_type_id = mapping.room_type_id
                property_id = mapping.property_id

        return CanonicalBooking(
            source_type=self.source_type,
            source_reference=event_data.get("uid"),
            property_id=property_id,
            room_type_id=room_type_id,
            guest_name=event_data.get("summary"),
            check_in=event_data.get("dtstart"),
            check_out=event_data.get("dtend"),
            number_of_guests=raw_payload.get("guests"),
            gross_amount=raw_payload.get("gross_amount", 0),
            total_amount=raw_payload.get("total_amount", 0),
            currency=raw_payload.get("currency", "INR"),
            special_requests=event_data.get("description"),
            raw_payload=raw_payload,
            metadata={"channel": "ical_feed", "feed_url": feed_url},
        )
