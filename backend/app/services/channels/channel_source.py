from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.repositories.booking import BookingRepository
from app.services.channels.canonical_booking import CanonicalBooking


class ChannelSource(ABC):
    """Abstract base class for all booking ingest channels."""

    source_type: str = ""

    @abstractmethod
    async def normalize(self, raw_payload: dict[str, Any]) -> CanonicalBooking:
        """Convert a raw source-specific payload into a CanonicalBooking."""
        ...

    async def validate(self, canonical: CanonicalBooking) -> bool:
        """Validate that the canonical booking has all required fields."""
        required = [
            canonical.property_id,
            canonical.check_in,
            canonical.check_out,
            canonical.source_type,
        ]
        return all(field is not None for field in required)

    async def create_booking(
        self, canonical: CanonicalBooking, db_session: AsyncSession
    ) -> Booking:
        """Persist a CanonicalBooking as a Booking record (stub for MVP).

        If ``org_id`` is present in ``canonical.metadata``, the booking is
        created via the repository.  Otherwise a transient ``Booking`` instance
        is returned so the method can be exercised in tests without a real org.
        """
        booking_data = canonical.to_booking_create()
        line_items = canonical.to_line_items()

        line_items_data = [
            {
                "item_type": li["item_type"],
                "item_id": li["item_id"],
                "quantity": li["quantity"],
                "unit_price": li["unit_price"],
                "nights": li["nights"],
                "total_price": li["total_price"],
            }
            for li in line_items
        ]

        if line_items_data:
            booking_data["line_items_data"] = line_items_data

        org_id = canonical.metadata.get("org_id")
        if org_id is not None:
            repo = BookingRepository(db_session, org_id)
            return await repo.create_with_line_items(booking_data, line_items=None)

        # Stub path: return a transient Booking object for testing / interface validation
        # Remove line_items_data since it is a schema field, not a model column
        stub_data = {k: v for k, v in booking_data.items() if k != "line_items_data"}
        return Booking(**stub_data)
