import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import BookingConflictError
from app.models.booking import Booking, BookingStatus
from app.models.inventory_hold import InventoryHold
from app.models.property import Property
from app.models.room_type import RoomType
from app.services.booking_service import BookingInitService
from app.services.inventory_service import InventoryService

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class FakeRedis:
    def __init__(self):
        self._data = {}

    async def get(self, key):
        return self._data.get(key)

    async def setex(self, key, seconds, value):
        self._data[key] = value

    async def delete(self, key):
        if key in self._data:
            del self._data[key]
            return 1
        return 0


async def _create_property(session: AsyncSession) -> Property:
    prop = Property(
        org_id=DEFAULT_ORG_ID,
        name="Test Retreat",
        address="Dharamkot",
    )
    session.add(prop)
    await session.flush()
    await session.refresh(prop)
    return prop


async def _create_room_type(
    session: AsyncSession, property_id: uuid.UUID, count: int = 5
) -> RoomType:
    rt = RoomType(
        org_id=DEFAULT_ORG_ID,
        property_id=property_id,
        name="Deluxe Room",
        count=count,
        base_capacity=2,
        max_capacity=3,
        default_rate=Decimal("2500.00"),
    )
    session.add(rt)
    await session.flush()
    await session.refresh(rt)
    return rt


async def _create_payment_failed_booking(
    session: AsyncSession,
    property_id: uuid.UUID,
    room_type_id: uuid.UUID,
    with_hold: bool = True,
    hold_status: str = "active",
) -> Booking:
    check_in = date.today() + timedelta(days=7)
    check_out = check_in + timedelta(days=2)
    booking = Booking(
        org_id=DEFAULT_ORG_ID,
        booking_type="room",
        source_type="direct",
        property_id=property_id,
        check_in=check_in,
        check_out=check_out,
        status=BookingStatus.payment_failed.value,
        gross_amount=Decimal("5000.00"),
        discount_amount=Decimal("0.00"),
        tax_amount=Decimal("600.00"),
        total_amount=Decimal("5600.00"),
        currency="INR",
        line_items=[
            {
                "item_type": "room",
                "item_id": str(room_type_id),
                "quantity": 1,
                "nights": 2,
                "unit_price": float(Decimal("2500.00")),
                "total_price": float(Decimal("5000.00")),
            }
        ],
    )
    session.add(booking)
    await session.flush()
    await session.refresh(booking)

    if with_hold:
        inv_svc = InventoryService(session)
        hold_id = await inv_svc.hold_inventory(
            booking_id=booking.id,
            property_id=property_id,
            room_type_id=room_type_id,
            dates=[check_in, check_in + timedelta(days=1)],
        )
        if hold_status != "active":
            result = await session.execute(
                select(InventoryHold).where(InventoryHold.id == uuid.UUID(hold_id))
            )
            hold = result.scalar_one()
            hold.status = hold_status
            if hold_status == "released":
                hold.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
            await session.flush()
        await session.commit()
    else:
        await session.commit()

    return booking


@pytest.mark.asyncio
async def test_retry_payment_reholds_inventory(db_session: AsyncSession):
    """Retry creates a new hold when the old one was released."""
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=1)
    await db_session.commit()
    booking = await _create_payment_failed_booking(
        db_session, prop.id, rt.id, with_hold=True, hold_status="released"
    )

    fake_redis = FakeRedis()
    svc = BookingInitService(db_session, DEFAULT_ORG_ID, fake_redis)
    resp = await svc.retry_payment(booking.id)

    assert resp.booking_id == booking.id
    assert resp.hold_id is not None

    # Verify a new active hold was created
    holds_result = await db_session.execute(
        select(InventoryHold).where(InventoryHold.booking_id == booking.id)
    )
    holds = holds_result.scalars().all()
    active_holds = [h for h in holds if h.status == "active"]
    assert len(active_holds) == 1
    assert str(active_holds[0].id) == resp.hold_id

    # Verify booking transitioned back to pending_payment
    booking_result = await db_session.execute(
        select(Booking).where(Booking.id == booking.id)
    )
    updated_booking = booking_result.scalar_one()
    assert updated_booking.status == BookingStatus.pending_payment.value


@pytest.mark.asyncio
async def test_retry_payment_reuses_active_hold(db_session: AsyncSession):
    """Retry reuses the existing hold when it is still active."""
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=1)
    await db_session.commit()
    booking = await _create_payment_failed_booking(
        db_session, prop.id, rt.id, with_hold=True, hold_status="active"
    )

    fake_redis = FakeRedis()
    svc = BookingInitService(db_session, DEFAULT_ORG_ID, fake_redis)
    resp = await svc.retry_payment(booking.id)

    assert resp.hold_id is not None

    # Should still have exactly one hold
    holds_result = await db_session.execute(
        select(InventoryHold).where(InventoryHold.booking_id == booking.id)
    )
    holds = holds_result.scalars().all()
    assert len(holds) == 1
    assert str(holds[0].id) == resp.hold_id
    assert holds[0].status == "active"


@pytest.mark.asyncio
async def test_retry_payment_no_inventory_returns_409(db_session: AsyncSession):
    """Retry raises BookingConflictError when inventory is exhausted."""
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=1)
    await db_session.commit()
    booking = await _create_payment_failed_booking(
        db_session, prop.id, rt.id, with_hold=True, hold_status="released"
    )

    # Consume the only room with another hold
    inv_svc = InventoryService(db_session)
    await inv_svc.hold_inventory(
        booking_id=uuid.uuid4(),
        property_id=prop.id,
        room_type_id=rt.id,
        dates=[booking.check_in, booking.check_in + timedelta(days=1)],
    )

    fake_redis = FakeRedis()
    svc = BookingInitService(db_session, DEFAULT_ORG_ID, fake_redis)
    with pytest.raises(BookingConflictError, match="Insufficient inventory"):
        await svc.retry_payment(booking.id)


@pytest.mark.asyncio
async def test_retry_payment_max_retries(db_session: AsyncSession):
    """Retry is blocked after 3 attempts."""
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=1)
    await db_session.commit()
    booking = await _create_payment_failed_booking(
        db_session, prop.id, rt.id, with_hold=True, hold_status="active"
    )

    fake_redis = FakeRedis()
    await fake_redis.setex(f"retry:{booking.id}", 3600, "3")

    svc = BookingInitService(db_session, DEFAULT_ORG_ID, fake_redis)
    with pytest.raises(ValueError, match="Maximum retry attempts exceeded"):
        await svc.retry_payment(booking.id)


@pytest.mark.asyncio
async def test_retry_payment_confirmed_rejected(db_session: AsyncSession):
    """Retry is rejected for a confirmed booking."""
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=1)
    await db_session.commit()
    booking = await _create_payment_failed_booking(
        db_session, prop.id, rt.id, with_hold=True, hold_status="active"
    )
    booking.status = BookingStatus.confirmed.value
    await db_session.commit()

    fake_redis = FakeRedis()
    svc = BookingInitService(db_session, DEFAULT_ORG_ID, fake_redis)
    with pytest.raises(ValueError, match="payment_failed status to retry"):
        await svc.retry_payment(booking.id)
