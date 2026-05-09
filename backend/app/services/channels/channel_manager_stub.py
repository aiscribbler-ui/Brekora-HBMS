from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ota_mapping import OTAMapping
from app.services.channels.canonical_booking import CanonicalBooking
from app.services.channels.channel_source import ChannelSource


class ChannelManagerStub(ChannelSource):
    """Skeleton for channel-manager integration (e.g. Staah, SiteMinder).

    The normalize() method maps channel-manager room codes to internal
    room_type_id via OTAMapping. External OAuth, webhook, and polling
    calls raise NotImplementedError until real credentials are provided.
    """

    source_type = "channel_manager"

    async def _resolve_room_mapping(
        self,
        db_session: AsyncSession,
        org_id: Any,
        external_room_code: str,
    ) -> OTAMapping | None:
        """Look up an OTAMapping row by channel-manager room code."""
        stmt = (
            select(OTAMapping)
            .where(
                OTAMapping.org_id == org_id,
                OTAMapping.ota_source == self.source_type,
                OTAMapping.listing_id == external_room_code,
                OTAMapping.is_active.is_(True),
                OTAMapping.is_archived.is_(False),
            )
        )
        result = await db_session.execute(stmt)
        return result.scalar_one_or_none()

    async def authenticate(self, api_key: str | None = None) -> dict[str, Any]:
        """Authenticate with the channel manager API.

        Raises NotImplementedError until real credentials are configured.
        """
        raise NotImplementedError(
            "Channel manager OAuth/API-key auth is not yet configured. "
            "Set credentials in settings and implement the auth flow."
        )

    async def handle_webhook(self, payload: dict[str, Any]) -> CanonicalBooking:
        """Process a push-based booking update from the channel manager.

        Raises NotImplementedError until a webhook endpoint is wired up.
        """
        raise NotImplementedError(
            "Channel manager webhook listener is not yet implemented. "
            "Add a FastAPI route that calls this method."
        )

    async def poll_sync(
        self,
        db_session: AsyncSession,
        org_id: Any,
        since: str | None = None,
    ) -> list[CanonicalBooking]:
        """Pull recent bookings from the channel manager API.

        Raises NotImplementedError until the external API client is built.
        """
        raise NotImplementedError(
            "Channel manager polling adapter is not yet implemented. "
            "Build the external API client and call this from a scheduled task."
        )

    async def normalize(
        self,
        raw_payload: dict[str, Any],
        db_session: AsyncSession | None = None,
        org_id: Any | None = None,
    ) -> CanonicalBooking:
        """Convert a channel-manager payload into a CanonicalBooking.

        If db_session and org_id are provided, attempts to resolve the
        external room code to an internal room_type_id via OTAMapping.
        """
        external_room_code = raw_payload.get("room_code") or raw_payload.get("listing_id")
        room_type_id = None
        property_id = None

        if db_session and org_id and external_room_code:
            mapping = await self._resolve_room_mapping(
                db_session, org_id, external_room_code
            )
            if mapping:
                room_type_id = mapping.room_type_id
                property_id = mapping.property_id

        return CanonicalBooking(
            source_type=self.source_type,
            source_reference=raw_payload.get("booking_reference"),
            property_id=property_id or raw_payload.get("property_id"),
            room_type_id=room_type_id or raw_payload.get("room_type_id"),
            guest_name=raw_payload.get("guest_name"),
            guest_email=raw_payload.get("guest_email"),
            check_in=raw_payload.get("check_in"),
            check_out=raw_payload.get("check_out"),
            number_of_guests=raw_payload.get("number_of_guests"),
            gross_amount=raw_payload.get("gross_amount", "0.00"),
            total_amount=raw_payload.get("total_amount", "0.00"),
            currency=raw_payload.get("currency", "INR"),
            raw_payload=raw_payload,
            metadata={
                "channel": self.source_type,
                "external_room_code": external_room_code,
                "mapped": room_type_id is not None,
            },
        )
