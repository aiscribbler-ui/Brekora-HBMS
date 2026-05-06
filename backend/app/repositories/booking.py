import uuid
from datetime import date
from typing import Any

from sqlalchemy import func, select

from app.models.booking import Booking, BookingLineItem
from app.repositories.base import OrgScopedRepository


class BookingRepository(OrgScopedRepository[Booking]):
    @property
    def model_class(self) -> type[Booking]:
        return Booking

    async def get_by_guest(
        self, guest_id: uuid.UUID, *, skip: int = 0, limit: int = 100
    ) -> list[Booking]:
        stmt = (
            select(Booking)
            .where(Booking.guest_id == guest_id)
            .offset(skip)
            .limit(limit)
        )
        stmt = self._apply_org_scope(stmt)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_property(
        self, property_id: uuid.UUID, *, skip: int = 0, limit: int = 100
    ) -> list[Booking]:
        stmt = (
            select(Booking)
            .where(Booking.property_id == property_id)
            .offset(skip)
            .limit(limit)
        )
        stmt = self._apply_org_scope(stmt)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_date_range(
        self,
        check_in_from: date,
        check_in_to: date,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Booking]:
        stmt = (
            select(Booking)
            .where(Booking.check_in >= check_in_from)
            .where(Booking.check_in <= check_in_to)
            .offset(skip)
            .limit(limit)
        )
        stmt = self._apply_org_scope(stmt)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_idempotency_key(
        self, idempotency_key: str
    ) -> Booking | None:
        stmt = select(Booking).where(Booking.idempotency_key == idempotency_key)
        stmt = self._apply_org_scope(stmt)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_with_line_items(
        self, obj_in: dict[str, Any], line_items: list[dict[str, Any]] | None = None
    ) -> Booking:
        obj_in["org_id"] = self.org_id
        db_obj = self.model_class(**obj_in)
        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)

        if line_items:
            for li in line_items:
                li_obj = BookingLineItem(booking_id=db_obj.id, **li)
                self.session.add(li_obj)
            await self.session.flush()
            await self.session.refresh(db_obj)

        return db_obj

    async def get_filtered(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        status: str | None = None,
        check_in_from: date | None = None,
        check_in_to: date | None = None,
        check_out_from: date | None = None,
        check_out_to: date | None = None,
    ) -> list[Booking]:
        stmt = select(Booking).offset(skip).limit(limit)
        if status is not None:
            stmt = stmt.where(Booking.status == status)
        if check_in_from is not None:
            stmt = stmt.where(Booking.check_in >= check_in_from)
        if check_in_to is not None:
            stmt = stmt.where(Booking.check_in <= check_in_to)
        if check_out_from is not None:
            stmt = stmt.where(Booking.check_out >= check_out_from)
        if check_out_to is not None:
            stmt = stmt.where(Booking.check_out <= check_out_to)
        stmt = self._apply_org_scope(stmt)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_check_in(self, target_date: date) -> int:
        stmt = (
            select(func.count())
            .select_from(Booking)
            .where(Booking.org_id == self.org_id)
            .where(Booking.check_in == target_date)
            .where(Booking.status == "confirmed")
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def count_by_check_out(self, target_date: date) -> int:
        stmt = (
            select(func.count())
            .select_from(Booking)
            .where(Booking.org_id == self.org_id)
            .where(Booking.check_out == target_date)
            .where(Booking.status == "confirmed")
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def count_in_house(self, target_date: date) -> int:
        stmt = (
            select(func.count())
            .select_from(Booking)
            .where(Booking.org_id == self.org_id)
            .where(Booking.check_in <= target_date)
            .where(Booking.check_out > target_date)
            .where(Booking.status == "confirmed")
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def count_by_status(self, status: str) -> int:
        stmt = (
            select(func.count())
            .select_from(Booking)
            .where(Booking.org_id == self.org_id)
            .where(Booking.status == status)
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0


class BookingLineItemRepository(OrgScopedRepository[BookingLineItem]):
    @property
    def model_class(self) -> type[BookingLineItem]:
        return BookingLineItem
