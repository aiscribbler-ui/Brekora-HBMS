import uuid
from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import BookingConflictError
from app.models.add_on import AddOn, AddOnType
from app.models.add_on_capacity import AddOnCapacity
from app.models.booking import Booking, BookingStatus
from app.models.inventory_hold import InventoryHold
from app.models.property import Property
from app.models.room_type import RoomType
from app.schemas.booking import AddOnSelection, BookingInitRequest
from app.services.booking_service import BookingInitService

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


async def _create_slot_add_on(
    session: AsyncSession, property_id: uuid.UUID
) -> AddOn:
    addon = AddOn(
        org_id=DEFAULT_ORG_ID,
        property_id=property_id,
        name="Massage",
        type=AddOnType.slot,
        is_active=True,
        unit_price=Decimal("1200.00"),
    )
    session.add(addon)
    await session.flush()
    await session.refresh(addon)
    return addon


async def _create_addon_capacity(
    session: AsyncSession,
    add_on_id: uuid.UUID,
    query_date: date,
    slot_time: time,
    total: int = 5,
) -> AddOnCapacity:
    ac = AddOnCapacity(
        add_on_id=add_on_id,
        date=query_date,
        slot_time=slot_time,
        total_capacity=total,
        available_capacity=total,
    )
    session.add(ac)
    await session.flush()
    await session.refresh(ac)
    return ac


@pytest.mark.asyncio
async def test_init_booking_with_valid_slot_time(db_session: AsyncSession):
    """Booking init succeeds when a valid slot time is selected."""
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)
    addon = await _create_slot_add_on(db_session, prop.id)
    query_date = date.today() + timedelta(days=7)
    await _create_addon_capacity(db_session, addon.id, query_date, time(10, 0), total=5)
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
                quantity=1,
                slot_time=time(10, 0),
            )
        ],
    )

    resp = await svc.init_booking(data)
    assert resp.booking_id is not None
    assert resp.hold_id is not None

    # Verify the hold records the slot time
    hold_uuid = uuid.UUID(resp.hold_id)
    result = await db_session.execute(
        select(InventoryHold).where(InventoryHold.id == hold_uuid)
    )
    hold = result.scalar_one()
    assert hold.add_on_holds is not None
    assert len(hold.add_on_holds) == 1
    assert hold.add_on_holds[0]["slot_time"] == "10:00:00"

    # Verify booking is pending_payment
    booking_result = await db_session.execute(
        select(Booking).where(Booking.id == resp.booking_id)
    )
    booking = booking_result.scalar_one()
    assert booking.status == BookingStatus.pending_payment.value


@pytest.mark.asyncio
async def test_init_booking_with_unavailable_slot_time(db_session: AsyncSession):
    """Booking init raises BookingConflictError when the requested slot is unavailable."""
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)
    addon = await _create_slot_add_on(db_session, prop.id)
    query_date = date.today() + timedelta(days=7)
    # Only 10:00 is available; 11:00 has no capacity row
    await _create_addon_capacity(db_session, addon.id, query_date, time(10, 0), total=5)
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
                quantity=1,
                slot_time=time(11, 0),
            )
        ],
    )

    with pytest.raises(BookingConflictError) as exc_info:
        await svc.init_booking(data)

    assert "Slot 11:00:00 for Massage is not available" in str(exc_info.value)


@pytest.mark.asyncio
async def test_init_booking_slot_alternatives_include_other_slots(db_session: AsyncSession):
    """Conflict alternatives for slot errors include other available slot times."""
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)
    addon = await _create_slot_add_on(db_session, prop.id)
    query_date = date.today() + timedelta(days=7)
    await _create_addon_capacity(db_session, addon.id, query_date, time(10, 0), total=5)
    await _create_addon_capacity(db_session, addon.id, query_date, time(14, 0), total=3)
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
                quantity=1,
                slot_time=time(11, 0),
            )
        ],
    )

    with pytest.raises(BookingConflictError) as exc_info:
        await svc.init_booking(data)

    alts = exc_info.value.alternatives
    assert len(alts) == 2

    # Verify alternative structure
    for alt in alts:
        assert alt["item_type"] == "add_on_slot"
        assert alt["item_id"] == addon.id
        assert alt["currency"] == "INR"
        assert alt["suggested_price"] == Decimal("1200.00")

    names = {alt["item_name"] for alt in alts}
    assert "Massage at 10:00:00" in names
    assert "Massage at 14:00:00" in names

    # Verify available counts
    ten_alt = next(a for a in alts if "10:00:00" in a["item_name"])
    fourteen_alt = next(a for a in alts if "14:00:00" in a["item_name"])
    assert ten_alt["available_count"] == 5
    assert fourteen_alt["available_count"] == 3
