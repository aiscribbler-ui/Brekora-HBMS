import uuid

from sqlalchemy import select

from app.models.room_type import RoomType
from app.repositories.base import OrgScopedRepository


class RoomTypeRepository(OrgScopedRepository[RoomType]):
    @property
    def model_class(self) -> type[RoomType]:
        return RoomType

    async def get_multi_by_property(
        self, property_id: uuid.UUID, *, skip: int = 0, limit: int = 100
    ) -> list[RoomType]:
        stmt = (
            select(RoomType)
            .where(RoomType.property_id == property_id)
            .offset(skip)
            .limit(limit)
        )
        stmt = self._apply_org_scope(stmt)
        result = await self.session.execute(stmt)
        return result.scalars().all()
