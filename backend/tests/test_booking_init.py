import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.add_on import AddOn, AddOnType
from app.models.add_on_capacity import AddOnCapacity
from app.models.booking import Booking, BookingStatus
from app.models.inventory_hold import InventoryHold
from app.models.property import Property
from app.models.room_type import RoomType
from app.schemas.booking import AddOnSelection, BookingInitRequest
from app.services.booking_service import BookingInitService
from app.services.inventory_service import InventoryService

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class FakeRedis:
    """Minimal fake Redis for idempotency tests."""

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


async def _create_add_on(
    session: AsyncSession, property_id: uuid.UUID
) -> AddOn:
    addon = AddOn(
        org_id=DEFAULT_ORG_ID,
        property_id=property_id,
        name="Yoga Class",
        type=AddOnType.day,
        is_active=True,
    )
    session.add(addon)
    await session.flush()
    await session.refresh(addon)
    return addon


async def _create_addon_capacity(
    session: AsyncSession, add_on_id: uuid.UUID, query_date: date, total: int = 10
) -> AddOnCapacity:
    ac = AddOnCapacity(
        add_on_id=add_on_id,
        date=query_date,
        total_capacity=total,
    )
    session.add(ac)
    await session.flush()
    await session.refresh(ac)
    return ac


@pytest.mark.asyncio
async def test_init_booking_room_success(db_session: AsyncSession):
    """Successful booking initialization with room hold."""
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)
    await db_session.commit()

    fake_redis = FakeRedis()
    svc = BookingInitService(db_session, DEFAULT_ORG_ID, fake_redis)

    check_in = date.today() + timedelta(days=7)
    check_out = check_in + timedelta(days=2)

    data = BookingInitRequest(
        property_id=prop.id,
        item_type="room",
        item_id=rt.id,
        check_in=check_in,
        check_out=check_out,
        guests=2,
    )

    resp = await svc.init_booking(data)

    assert resp.booking_id is not None
    assert resp.hold_id is not None
    assert resp.hold_expires_at > datetime.now(timezone.utc)  # future datetime
    assert resp.amount_breakdown.total_amount > 0
    assert resp.amount_breakdown.currency == "INR"

    # Verify booking record
    result = await db_session.execute(
        select(Booking).where(Booking.id == resp.booking_id)
    )
    booking = result.scalar_one()
    assert booking.status == BookingStatus.pending_payment.value
    assert booking.property_id == prop.id
    assert booking.booking_type == "room"

    # Verify hold record
    hold_uuid = uuid.UUID(resp.hold_id)
    result = await db_session.execute(
        select(InventoryHold).where(InventoryHold.id == hold_uuid)
    )
    hold = result.scalar_one()
    assert hold.status == "active"
    assert hold.booking_id == resp.booking_id
    assert hold.room_type_id == rt.id


@pytest.mark.asyncio
async def test_init_booking_with_addons(db_session: AsyncSession):
    """Booking init with add-on selections."""
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)
    addon = await _create_add_on(db_session, prop.id)
    query_date = date.today() + timedelta(days=7)
    await _create_addon_capacity(db_session, addon.id, query_date, total=10)
    await db_session.commit()

    fake_redis = FakeRedis()
    svc = BookingInitService(db_session, DEFAULT_ORG_ID, fake_redis)

    data = BookingInitRequest(
        property_id=prop.id,
        item_type="room",
        item_id=rt.id,
        check_in=query_date,
        check_out=query_date + timedelta(days=1),
        guests=2,
        add_on_selections=[
            AddOnSelection(
                add_on_id=addon.id,
                date=query_date,
                quantity=2,
            )
        ],
    )

    resp = await svc.init_booking(data)
    assert resp.booking_id is not None
    assert resp.hold_id is not None

    # Verify hold has add_on_holds
    hold_uuid = uuid.UUID(resp.hold_id)
    result = await db_session.execute(
        select(InventoryHold).where(InventoryHold.id == hold_uuid)
    )
    hold = result.scalar_one()
    assert hold.add_on_holds is not None
    assert len(hold.add_on_holds) >= 1


@pytest.mark.asyncio
async def test_init_booking_idempotency(db_session: AsyncSession):
    """Duplicate idempotency key returns existing booking without double-hold."""
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)
    await db_session.commit()

    fake_redis = FakeRedis()
    svc = BookingInitService(db_session, DEFAULT_ORG_ID, fake_redis)

    check_in = date.today() + timedelta(days=7)
    check_out = check_in + timedelta(days=1)

    data = BookingInitRequest(
        property_id=prop.id,
        item_type="room",
        item_id=rt.id,
        check_in=check_in,
        check_out=check_out,
        guests=2,
        idempotency_key="unique-key-123",
    )

    resp1 = await svc.init_booking(data)

    # Second call with same key should return same booking
    resp2 = await svc.init_booking(data)
    assert resp1.booking_id == resp2.booking_id

    # Verify only one hold exists
    result = await db_session.execute(
        select(InventoryHold).where(InventoryHold.booking_id == resp1.booking_id)
    )
    holds = result.scalars().all()
    assert len(holds) == 1


@pytest.mark.asyncio
async def test_init_booking_insufficient_inventory(db_session: AsyncSession):
    """409 conflict when no rooms available."""
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=1)
    await db_session.commit()

    # Commit a hold to consume the only room
    inv_svc = InventoryService(db_session)
    dummy_booking_id = uuid.uuid4()
    await inv_svc.hold_inventory(
        booking_id=dummy_booking_id,
        property_id=prop.id,
        room_type_id=rt.id,
        dates=[date.today() + timedelta(days=7)],
    )

    fake_redis = FakeRedis()
    svc = BookingInitService(db_session, DEFAULT_ORG_ID, fake_redis)

    data = BookingInitRequest(
        property_id=prop.id,
        item_type="room",
        item_id=rt.id,
        check_in=date.today() + timedelta(days=7),
        check_out=date.today() + timedelta(days=8),
        guests=2,
    )

    with pytest.raises(ValueError, match="Insufficient inventory"):
        await svc.init_booking(data)


@pytest.mark.asyncio
async def test_init_booking_invalid_property(db_session: AsyncSession):
    """Error when property does not exist."""
    fake_redis = FakeRedis()
    svc = BookingInitService(db_session, DEFAULT_ORG_ID, fake_redis)

    data = BookingInitRequest(
        property_id=uuid.uuid4(),
        item_type="room",
        item_id=uuid.uuid4(),
        check_in=date.today() + timedelta(days=7),
        check_out=date.today() + timedelta(days=8),
        guests=2,
    )

    with pytest.raises(ValueError, match="Property not found"):
        await svc.init_booking(data)
