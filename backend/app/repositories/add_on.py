import uuid
from datetime import date, time

from sqlalchemy import select

from app.models.add_on import AddOn
from app.models.add_on_capacity import AddOnCapacity
from app.repositories.base import BaseRepository, OrgScopedRepository


class AddOnRepository(OrgScopedRepository[AddOn]):
    @property
    def model_class(self) -> type[AddOn]:
        return AddOn

    async def get_multi_by_property(
        self, property_id: uuid.UUID, *, skip: int = 0, limit: int = 100
    ) -> list[AddOn]:
        stmt = (
            select(AddOn)
            .where(AddOn.property_id == property_id)
            .offset(skip)
            .limit(limit)
        )
        stmt = self._apply_org_scope(stmt)
        result = await self.session.execute(stmt)
        return result.scalars().all()


class AddOnCapacityRepository(BaseRepository[AddOnCapacity]):
    @property
    def model_class(self) -> type[AddOnCapacity]:
        return AddOnCapacity

    async def get_multi_by_add_on(
        self, add_on_id: uuid.UUID, *, skip: int = 0, limit: int = 100
    ) -> list[AddOnCapacity]:
        stmt = (
            select(AddOnCapacity)
            .where(AddOnCapacity.add_on_id == add_on_id)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_add_on_date_slot(
        self, add_on_id: uuid.UUID, date: date, slot_time: time
    ) -> AddOnCapacity | None:
        stmt = (
            select(AddOnCapacity)
            .where(
                AddOnCapacity.add_on_id == add_on_id,
                AddOnCapacity.date == date,
                AddOnCapacity.slot_time == slot_time,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_add_on_date(
        self, add_on_id: uuid.UUID, date: date
    ) -> AddOnCapacity | None:
        stmt = (
            select(AddOnCapacity)
            .where(
                AddOnCapacity.add_on_id == add_on_id,
                AddOnCapacity.date == date,
                AddOnCapacity.slot_time.is_(None),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
