import uuid
from datetime import date

from sqlalchemy import select

from app.models.inventory_buffer import InventoryBuffer
from app.repositories.base import OrgScopedRepository


class InventoryBufferRepository(OrgScopedRepository[InventoryBuffer]):
    @property
    def model_class(self) -> type[InventoryBuffer]:
        return InventoryBuffer

    async def get_by_room_type_and_date(
        self, room_type_id: uuid.UUID, query_date: date
    ) -> InventoryBuffer | None:
        stmt = (
            select(InventoryBuffer)
            .where(InventoryBuffer.room_type_id == room_type_id)
            .where(InventoryBuffer.date == query_date)
        )
        stmt = self._apply_org_scope(stmt)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_property_and_date_range(
        self,
        property_id: uuid.UUID,
        start_date: date,
        end_date: date,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[InventoryBuffer]:
        stmt = (
            select(InventoryBuffer)
            .where(InventoryBuffer.property_id == property_id)
            .where(InventoryBuffer.date >= start_date)
            .where(InventoryBuffer.date <= end_date)
            .offset(skip)
            .limit(limit)
        )
        stmt = self._apply_org_scope(stmt)
        result = await self.session.execute(stmt)
        return result.scalars().all()
