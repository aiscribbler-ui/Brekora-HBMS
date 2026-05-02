import uuid
from decimal import Decimal

from sqlalchemy import select

from app.models.parsed_booking import ParsedBookingQueue
from app.repositories.base import OrgScopedRepository


class ParsedBookingQueueRepository(OrgScopedRepository[ParsedBookingQueue]):
    @property
    def model_class(self) -> type[ParsedBookingQueue]:
        return ParsedBookingQueue

    async def get_pending(
        self, *, skip: int = 0, limit: int = 100
    ) -> list[ParsedBookingQueue]:
        stmt = (
            select(ParsedBookingQueue)
            .where(ParsedBookingQueue.status == "pending")
            .offset(skip)
            .limit(limit)
        )
        stmt = self._apply_org_scope(stmt)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_source_type(
        self, source_type: str, *, skip: int = 0, limit: int = 100
    ) -> list[ParsedBookingQueue]:
        stmt = (
            select(ParsedBookingQueue)
            .where(ParsedBookingQueue.source_type == source_type)
            .offset(skip)
            .limit(limit)
        )
        stmt = self._apply_org_scope(stmt)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_confidence_range(
        self,
        min_score: Decimal,
        max_score: Decimal,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ParsedBookingQueue]:
        stmt = (
            select(ParsedBookingQueue)
            .where(ParsedBookingQueue.confidence_score >= min_score)
            .where(ParsedBookingQueue.confidence_score <= max_score)
            .offset(skip)
            .limit(limit)
        )
        stmt = self._apply_org_scope(stmt)
        result = await self.session.execute(stmt)
        return result.scalars().all()
