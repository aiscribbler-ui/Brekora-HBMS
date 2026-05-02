import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking, BookingStatus
from app.models.inventory_hold import InventoryHold
from app.models.payment import Payment
from app.models.property import Property
from app.models.room_type import RoomType
from app.services.inventory_service import InventoryService
from app.services.payment_service import PaymentService

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class FakeRedis:
    """Minimal fake Redis for tests."""

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


async def _create_booking(session: AsyncSession, property_id: uuid.UUID, room_type_id: uuid.UUID) -> Booking:
    check_in = date.today() + timedelta(days=7)
    check_out = check_in + timedelta(days=2)
    booking = Booking(
        org_id=DEFAULT_ORG_ID,
        booking_type="room",
        source_type="direct",
        property_id=property_id,
        check_in=check_in,
        check_out=check_out,
        status=BookingStatus.pending_payment.value,
        gross_amount=Decimal("5000.00"),
        discount_amount=Decimal("0.00"),
        tax_amount=Decimal("600.00"),
        total_amount=Decimal("5600.00"),
        currency="INR",
    )
    session.add(booking)
    await session.flush()
    await session.refresh(booking)

    # Create inventory hold
    inv_svc = InventoryService(session)
    hold_id = await inv_svc.hold_inventory(
        booking_id=booking.id,
        property_id=property_id,
        room_type_id=room_type_id,
        dates=[check_in, check_in + timedelta(days=1)],
    )
    await session.commit()
    return booking


@pytest.mark.asyncio
async def test_create_order_success(db_session: AsyncSession):
    """PaymentService.create_order returns Razorpay order dict."""
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)
    await db_session.commit()

    booking = await _create_booking(db_session, prop.id, rt.id)

    fake_redis = FakeRedis()
    svc = PaymentService(db_session, DEFAULT_ORG_ID, fake_redis)
    order = await svc.create_order(booking.id)

    assert order["id"].startswith("order_")
    assert order["amount"] == 560000  # paise
    assert order["currency"] == "INR"
    assert order["status"] == "created"

    # Verify payment record created
    result = await db_session.execute(
        select(Payment).where(Payment.booking_id == booking.id)
    )
    payment = result.scalar_one_or_none()
    assert payment is not None
    assert payment.amount == Decimal("5600.00")
    assert payment.status == "created"


@pytest.mark.asyncio
async def test_create_order_requires_pending_payment(db_session: AsyncSession):
    """Order creation rejected if booking is not pending_payment."""
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)
    await db_session.commit()

    booking = await _create_booking(db_session, prop.id, rt.id)
    booking.status = BookingStatus.confirmed.value
    await db_session.commit()

    fake_redis = FakeRedis()
    svc = PaymentService(db_session, DEFAULT_ORG_ID, fake_redis)
    with pytest.raises(ValueError, match="pending_payment"):
        await svc.create_order(booking.id)


@pytest.mark.asyncio
async def test_create_order_amount_matches_booking_total(db_session: AsyncSession):
    """Order amount (in paise) equals booking total * 100."""
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)
    await db_session.commit()

    booking = await _create_booking(db_session, prop.id, rt.id)
    booking.total_amount = Decimal("9999.99")
    await db_session.commit()

    fake_redis = FakeRedis()
    svc = PaymentService(db_session, DEFAULT_ORG_ID, fake_redis)
    order = await svc.create_order(booking.id)
    assert order["amount"] == 999999
