from sqlalchemy import select

from app.models.role import Role
from app.repositories.base import OrgScopedRepository


class RoleRepository(OrgScopedRepository[Role]):
    @property
    def model_class(self) -> type[Role]:
        return Role

    async def get_by_name(self, name: str) -> Role | None:
        stmt = select(Role).where(Role.name == name)
        stmt = self._apply_org_scope(stmt)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
