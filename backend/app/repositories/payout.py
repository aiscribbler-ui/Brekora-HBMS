import uuid

from sqlalchemy import select

from app.models.payout import Payout
from app.repositories.base import OrgScopedRepository


class PayoutRepository(OrgScopedRepository[Payout]):
    @property
    def model_class(self) -> type[Payout]:
        return Payout

    async def get_by_property_and_month(
        self, property_id: uuid.UUID, month: str
    ) -> Payout | None:
        stmt = (
            select(Payout)
            .where(Payout.property_id == property_id)
            .where(Payout.month == month)
        )
        stmt = self._apply_org_scope(stmt)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
