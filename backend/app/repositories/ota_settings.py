import uuid

from sqlalchemy import select

from app.models.ota_settings import OTASettings
from app.repositories.base import OrgScopedRepository


class OTASettingsRepository(OrgScopedRepository[OTASettings]):
    @property
    def model_class(self) -> type[OTASettings]:
        return OTASettings

    async def get_by_ota_source(self, ota_source: str) -> OTASettings | None:
        stmt = select(OTASettings).where(OTASettings.ota_source == ota_source)
        stmt = self._apply_org_scope(stmt)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
