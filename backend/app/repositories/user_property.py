import uuid

from sqlalchemy import select

from app.models.user_property import UserProperty
from app.repositories.base import BaseRepository


class UserPropertyRepository(BaseRepository[UserProperty]):
    @property
    def model_class(self) -> type[UserProperty]:
        return UserProperty

    async def get_by_user(self, user_id: uuid.UUID) -> list[UserProperty]:
        stmt = select(UserProperty).where(
            UserProperty.user_id == user_id,
            UserProperty.is_active == True,
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_user_and_property(
        self, user_id: uuid.UUID, property_id: uuid.UUID
    ) -> UserProperty | None:
        stmt = select(UserProperty).where(
            UserProperty.user_id == user_id,
            UserProperty.property_id == property_id,
            UserProperty.is_active == True,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
