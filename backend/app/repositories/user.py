import uuid

from sqlalchemy import select

from app.models.user import User
from app.repositories.base import OrgScopedRepository


class UserRepository(OrgScopedRepository[User]):
    @property
    def model_class(self) -> type[User]:
        return User

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        stmt = self._apply_org_scope(stmt)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email_unscoped(self, email: str) -> User | None:
        """Look up user by email without org scoping. Used for login when caller does not yet know the org."""
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
