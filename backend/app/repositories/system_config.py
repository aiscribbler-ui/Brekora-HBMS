import uuid

from sqlalchemy import select

from app.models.system_config import SystemConfig
from app.repositories.base import OrgScopedRepository


class SystemConfigRepository(OrgScopedRepository[SystemConfig]):
    @property
    def model_class(self) -> type[SystemConfig]:
        return SystemConfig

    async def get_by_key(self, key: str) -> SystemConfig | None:
        stmt = select(SystemConfig).where(
            SystemConfig.key == key,
        )
        stmt = self._apply_org_scope(stmt)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
