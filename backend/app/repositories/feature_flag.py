import uuid

from sqlalchemy import select

from app.models.feature_flag import FeatureFlag
from app.repositories.base import OrgScopedRepository


class FeatureFlagRepository(OrgScopedRepository[FeatureFlag]):
    @property
    def model_class(self) -> type[FeatureFlag]:
        return FeatureFlag

    async def get_by_key(self, key: str) -> FeatureFlag | None:
        stmt = select(FeatureFlag).where(FeatureFlag.key == key)
        stmt = self._apply_org_scope(stmt)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
