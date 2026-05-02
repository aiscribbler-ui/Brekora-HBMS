import uuid

from sqlalchemy import select

from app.models.ota_mapping import OTAMapping
from app.repositories.base import OrgScopedRepository


class OTAMappingRepository(OrgScopedRepository[OTAMapping]):
    @property
    def model_class(self) -> type[OTAMapping]:
        return OTAMapping

    async def get_by_listing(
        self, ota_source: str, listing_id: str
    ) -> OTAMapping | None:
        stmt = (
            select(OTAMapping)
            .where(OTAMapping.ota_source == ota_source)
            .where(OTAMapping.listing_id == listing_id)
        )
        stmt = self._apply_org_scope(stmt)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
