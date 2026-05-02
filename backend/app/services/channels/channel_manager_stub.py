from typing import Any

from app.services.channels.canonical_booking import CanonicalBooking
from app.services.channels.channel_source import ChannelSource


class ChannelManagerStub(ChannelSource):
    """Empty stub for future channel-manager integration (e.g. Staah, SiteMinder).

    TODO:
      - Implement OAuth/API-key auth with channel manager
      - Implement webhook listener for push-based updates
      - Implement polling adapter for pull-based sync
      - Map channel-manager room codes to internal room_type_id via OTAMapping
    """

    source_type = "channel_manager"

    async def normalize(self, raw_payload: dict[str, Any]) -> CanonicalBooking:
        """Stub normalizer — returns an empty CanonicalBooking."""
        return CanonicalBooking(
            source_type=self.source_type,
            raw_payload=raw_payload,
            metadata={"channel": "channel_manager_stub"},
        )
