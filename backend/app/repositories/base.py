import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Non-scoped base repository for global tables such as Organization."""

    def __init__(self, session: AsyncSession):
        self.session = session

    @property
    def model_class(self) -> type[ModelType]:
        raise NotImplementedError

    async def get(self, id: uuid.UUID) -> ModelType | None:
        stmt = select(self.model_class).where(self.model_class.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self, *, skip: int = 0, limit: int = 100
    ) -> list[ModelType]:
        stmt = select(self.model_class).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, obj_in: dict[str, Any]) -> ModelType:
        db_obj = self.model_class(**obj_in)
        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def update(
        self, db_obj: ModelType, obj_in: dict[str, Any]
    ) -> ModelType:
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def delete(self, db_obj: ModelType) -> None:
        await self.session.delete(db_obj)
        await self.session.flush()


class OrgScopedRepository(BaseRepository[ModelType]):
    """Organization-scoped repository for multi-tenant domain models."""

    def __init__(self, session: AsyncSession, org_id: uuid.UUID):
        super().__init__(session)
        self.org_id = org_id

    def _apply_org_scope(self, stmt: Any) -> Any:
        if hasattr(self.model_class, "org_id"):
            stmt = stmt.where(self.model_class.org_id == self.org_id)
        return stmt

    async def get(self, id: uuid.UUID) -> ModelType | None:
        stmt = select(self.model_class).where(self.model_class.id == id)
        stmt = self._apply_org_scope(stmt)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self, *, skip: int = 0, limit: int = 100
    ) -> list[ModelType]:
        stmt = select(self.model_class).offset(skip).limit(limit)
        stmt = self._apply_org_scope(stmt)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, obj_in: dict[str, Any]) -> ModelType:
        obj_in["org_id"] = self.org_id
        return await super().create(obj_in)
