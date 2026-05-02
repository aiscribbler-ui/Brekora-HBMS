import uuid

from sqlalchemy import select

from app.models.payment import Payment
from app.repositories.base import OrgScopedRepository


class PaymentRepository(OrgScopedRepository[Payment]):
    @property
    def model_class(self) -> type[Payment]:
        return Payment

    async def get_by_booking_id(
        self, booking_id: uuid.UUID
    ) -> Payment | None:
        stmt = (
            select(Payment)
            .where(Payment.booking_id == booking_id)
        )
        stmt = self._apply_org_scope(stmt)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
