import uuid
from datetime import date

from sqlalchemy import select

from app.models.promo_code import PromoCode
from app.models.rate_plan import RatePlan
from app.models.seasonal_calendar import SeasonalCalendar
from app.repositories.base import OrgScopedRepository


class RatePlanRepository(OrgScopedRepository[RatePlan]):
    @property
    def model_class(self) -> type[RatePlan]:
        return RatePlan

    async def get_by_code(self, code: str, org_id: uuid.UUID | None = None) -> RatePlan | None:
        stmt = select(RatePlan).where(
            RatePlan.code == code,
            RatePlan.is_active == True,
        )
        if org_id is not None:
            stmt = stmt.where(RatePlan.org_id == org_id)
        else:
            stmt = self._apply_org_scope(stmt)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class SeasonalCalendarRepository(OrgScopedRepository[SeasonalCalendar]):
    @property
    def model_class(self) -> type[SeasonalCalendar]:
        return SeasonalCalendar

    async def get_active_for_date_range(
        self, start_date: date, end_date: date, org_id: uuid.UUID | None = None
    ) -> list[SeasonalCalendar]:
        stmt = select(SeasonalCalendar).where(
            SeasonalCalendar.is_active == True,
            SeasonalCalendar.start_date <= end_date,
            SeasonalCalendar.end_date >= start_date,
        )
        if org_id is not None:
            stmt = stmt.where(SeasonalCalendar.org_id == org_id)
        else:
            stmt = self._apply_org_scope(stmt)
        result = await self.session.execute(stmt)
        return result.scalars().all()


class PromoCodeRepository(OrgScopedRepository[PromoCode]):
    @property
    def model_class(self) -> type[PromoCode]:
        return PromoCode

    async def get_by_code(self, code: str, org_id: uuid.UUID | None = None) -> PromoCode | None:
        stmt = select(PromoCode).where(
            PromoCode.code == code,
        )
        if org_id is not None:
            stmt = stmt.where(PromoCode.org_id == org_id)
        else:
            stmt = self._apply_org_scope(stmt)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def increment_used_count(self, promo_code: PromoCode) -> None:
        promo_code.used_count += 1
        self.session.add(promo_code)
        await self.session.flush()
