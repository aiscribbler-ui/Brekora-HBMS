import uuid
from datetime import date, time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.add_on_capacity import AddOnCapacity


class AddOnSlotService:
    """Service for querying available time slots for slot-based add-ons."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_available_slots(
        self, add_on_id: uuid.UUID, query_date: date
    ) -> list[time]:
        """Return sorted list of slot times with positive capacity."""
        stmt = (
            select(AddOnCapacity)
            .where(
                AddOnCapacity.add_on_id == add_on_id,
                AddOnCapacity.date == query_date,
                AddOnCapacity.available_capacity > 0,
            )
            .order_by(AddOnCapacity.slot_time.asc())
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [r.slot_time for r in rows if r.slot_time is not None]
