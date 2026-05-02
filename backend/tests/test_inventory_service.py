import asyncio
import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.models.add_on import AddOn, AddOnType
from app.models.add_on_capacity import AddOnCapacity
from app.models.booking import Booking, BookingLineItem
from app.models.inventory_hold import InventoryHold
from app.models.property import Property
from app.models.room_type import RoomType
from app.services.inventory_service import InventoryService

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class FakeRedis:
    """Minimal fake Redis for TTL tests."""

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
        name="Test Hotel",
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
        name="Deluxe",
        count=count,
        base_capacity=2,
        max_capacity=3,
        default_rate=100.00,
    )
    session.add(rt)
    await session.flush()
    await session.refresh(rt)
    return rt


async def _create_booking(
    session: AsyncSession, property_id: uuid.UUID, check_in: date, check_out: date
) -> Booking:
    booking = Booking(
        org_id=DEFAULT_ORG_ID,
        booking_type="room",
        property_id=property_id,
        check_in=check_in,
        check_out=check_out,
    )
    session.add(booking)
    await session.flush()
    await session.refresh(booking)
    return booking


# ---------------------------------------------------------------------------
# Availability queries
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_check_availability_no_room_type(db_session: AsyncSession):
    svc = InventoryService(db_session)
    fake_id = uuid.uuid4()
    available = await svc.check_availability(
        fake_id, fake_id, date(2026, 5, 1), date(2026, 5, 3)
    )
    assert available == 0


@pytest.mark.asyncio(loop_scope="session")
async def test_check_availability_invalid_dates(db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)
    svc = InventoryService(db_session)

    available = await svc.check_availability(
        prop.id, rt.id, date(2026, 5, 3), date(2026, 5, 1)
    )
    assert available == 0

    available = await svc.check_availability(
        prop.id, rt.id, date(2026, 5, 1), date(2026, 5, 1)
    )
    assert available == 0


@pytest.mark.asyncio(loop_scope="session")
async def test_check_availability_basic(db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)
    svc = InventoryService(db_session)

    available = await svc.check_availability(
        prop.id, rt.id, date(2026, 5, 1), date(2026, 5, 3)
    )
    assert available == 5


@pytest.mark.asyncio(loop_scope="session")
async def test_check_availability_with_active_hold(db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)
    svc = InventoryService(db_session)

    # Create an active hold manually
    hold = InventoryHold(
        org_id=DEFAULT_ORG_ID,
        booking_id=uuid.uuid4(),
        property_id=prop.id,
        room_type_id=rt.id,
        dates=[date(2026, 5, 1), date(2026, 5, 2)],
        status="active",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db_session.add(hold)
    await db_session.flush()

    available = await svc.check_availability(
        prop.id, rt.id, date(2026, 5, 1), date(2026, 5, 3)
    )
    assert available == 4


@pytest.mark.asyncio(loop_scope="session")
async def test_check_availability_expired_hold_ignored(db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)
    svc = InventoryService(db_session)

    hold = InventoryHold(
        org_id=DEFAULT_ORG_ID,
        booking_id=uuid.uuid4(),
        property_id=prop.id,
        room_type_id=rt.id,
        dates=[date(2026, 5, 1)],
        status="active",
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    db_session.add(hold)
    await db_session.flush()

    available = await svc.check_availability(
        prop.id, rt.id, date(2026, 5, 1), date(2026, 5, 2)
    )
    assert available == 5


@pytest.mark.asyncio(loop_scope="session")
async def test_check_availability_multiple_nights(db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=3)
    svc = InventoryService(db_session)

    # Hold only on May 2nd
    hold = InventoryHold(
        org_id=DEFAULT_ORG_ID,
        booking_id=uuid.uuid4(),
        property_id=prop.id,
        room_type_id=rt.id,
        dates=[date(2026, 5, 2)],
        status="active",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db_session.add(hold)
    await db_session.flush()

    # Request May 1-4 (nights May 1, 2, 3)
    # May 1: 3 available, May 2: 2 available, May 3: 3 available
    available = await svc.check_availability(
        prop.id, rt.id, date(2026, 5, 1), date(2026, 5, 4)
    )
    assert available == 2


@pytest.mark.asyncio(loop_scope="session")
async def test_check_availability_counts_committed(db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=3)
    svc = InventoryService(db_session)

    hold = InventoryHold(
        org_id=DEFAULT_ORG_ID,
        booking_id=uuid.uuid4(),
        property_id=prop.id,
        room_type_id=rt.id,
        dates=[date(2026, 5, 2)],
        status="committed",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db_session.add(hold)
    await db_session.flush()

    available = await svc.check_availability(
        prop.id, rt.id, date(2026, 5, 1), date(2026, 5, 4)
    )
    assert available == 2


# ---------------------------------------------------------------------------
# Hold creation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_hold_inventory_success(db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=2)
    await db_session.commit()
    svc = InventoryService(db_session)

    booking_id = uuid.uuid4()
    hold_id = await svc.hold_inventory(
        booking_id=booking_id,
        property_id=prop.id,
        room_type_id=rt.id,
        dates=[date(2026, 5, 10), date(2026, 5, 11)],
    )

    assert isinstance(hold_id, str)
    uuid.UUID(hold_id)  # valid UUID

    # Verify hold was persisted
    hold = await db_session.get(InventoryHold, uuid.UUID(hold_id))
    assert hold is not None
    assert hold.booking_id == booking_id
    assert hold.property_id == prop.id
    assert hold.room_type_id == rt.id
    assert hold.status == "active"
    assert hold.dates == [date(2026, 5, 10), date(2026, 5, 11)]
    assert hold.expires_at > datetime.now(timezone.utc)


@pytest.mark.asyncio(loop_scope="session")
async def test_hold_inventory_reduces_availability(db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=2)
    await db_session.commit()
    svc = InventoryService(db_session)

    await svc.hold_inventory(
        booking_id=uuid.uuid4(),
        property_id=prop.id,
        room_type_id=rt.id,
        dates=[date(2026, 5, 10)],
    )

    available = await svc.check_availability(
        prop.id, rt.id, date(2026, 5, 10), date(2026, 5, 11)
    )
    assert available == 1

    await svc.hold_inventory(
        booking_id=uuid.uuid4(),
        property_id=prop.id,
        room_type_id=rt.id,
        dates=[date(2026, 5, 10)],
    )

    available = await svc.check_availability(
        prop.id, rt.id, date(2026, 5, 10), date(2026, 5, 11)
    )
    assert available == 0


@pytest.mark.asyncio(loop_scope="session")
async def test_hold_inventory_insufficient_inventory(db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=1)
    await db_session.commit()
    svc = InventoryService(db_session)

    await svc.hold_inventory(
        booking_id=uuid.uuid4(),
        property_id=prop.id,
        room_type_id=rt.id,
        dates=[date(2026, 5, 10)],
    )

    with pytest.raises(ValueError, match="Insufficient inventory"):
        await svc.hold_inventory(
            booking_id=uuid.uuid4(),
            property_id=prop.id,
            room_type_id=rt.id,
            dates=[date(2026, 5, 10)],
        )


@pytest.mark.asyncio(loop_scope="session")
async def test_hold_inventory_empty_dates(db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id)
    await db_session.commit()
    svc = InventoryService(db_session)

    with pytest.raises(ValueError, match="dates must not be empty"):
        await svc.hold_inventory(
            booking_id=uuid.uuid4(),
            property_id=prop.id,
            room_type_id=rt.id,
            dates=[],
        )


@pytest.mark.asyncio(loop_scope="session")
async def test_hold_inventory_redis_tracking(db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id)
    await db_session.commit()

    fake_redis = FakeRedis()
    svc = InventoryService(db_session, redis=fake_redis)
    hold_id = await svc.hold_inventory(
        booking_id=uuid.uuid4(),
        property_id=prop.id,
        room_type_id=rt.id,
        dates=[date(2026, 5, 10)],
    )
    assert await fake_redis.get(f"hold:{hold_id}") is not None


# ---------------------------------------------------------------------------
# Add-on availability and holds
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_check_addon_availability(db_session: AsyncSession):
    prop = await _create_property(db_session)
    addon = AddOn(
        org_id=DEFAULT_ORG_ID,
        property_id=prop.id,
        name="Breakfast",
        type=AddOnType.slot,
        default_capacity=0,
        unit_price=50.00,
    )
    db_session.add(addon)
    await db_session.flush()

    cap = AddOnCapacity(
        add_on_id=addon.id,
        date=date(2026, 5, 10),
        slot_time=time(9, 0),
        total_capacity=5,
        available_capacity=5,
    )
    db_session.add(cap)
    await db_session.flush()

    svc = InventoryService(db_session)
    avail = await svc.check_addon_availability(
        addon.id, date(2026, 5, 10), time(9, 0), 1
    )
    assert avail == 5

    # Simulate a committed hold
    booking = await _create_booking(
        db_session, prop.id, date(2026, 5, 10), date(2026, 5, 11)
    )
    hold = InventoryHold(
        org_id=DEFAULT_ORG_ID,
        booking_id=booking.id,
        property_id=prop.id,
        room_type_id=uuid.uuid4(),
        dates=[date(2026, 5, 10)],
        add_on_holds=[
            {
                "add_on_id": str(addon.id),
                "date": "2026-05-10",
                "slot_time": "09:00:00",
                "quantity": 2,
            }
        ],
        status="committed",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db_session.add(hold)
    await db_session.flush()

    avail = await svc.check_addon_availability(
        addon.id, date(2026, 5, 10), time(9, 0), 1
    )
    assert avail == 3


@pytest.mark.asyncio(loop_scope="session")
async def test_hold_inventory_with_addons(db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)
    addon = AddOn(
        org_id=DEFAULT_ORG_ID,
        property_id=prop.id,
        name="Spa",
        type=AddOnType.day,
        default_capacity=0,
        unit_price=100.00,
    )
    db_session.add(addon)
    await db_session.flush()

    cap = AddOnCapacity(
        add_on_id=addon.id,
        date=date(2026, 5, 10),
        total_capacity=5,
        available_capacity=5,
    )
    db_session.add(cap)
    await db_session.flush()
    await db_session.commit()

    svc = InventoryService(db_session)
    hold_id = await svc.hold_inventory(
        booking_id=uuid.uuid4(),
        property_id=prop.id,
        room_type_id=rt.id,
        dates=[date(2026, 5, 10)],
        add_on_items=[
            {
                "add_on_id": str(addon.id),
                "date": "2026-05-10",
                "quantity": 2,
            }
        ],
    )
    hold = await db_session.get(InventoryHold, uuid.UUID(hold_id))
    assert hold is not None
    assert hold.add_on_holds is not None
    assert len(hold.add_on_holds) == 1
    assert hold.add_on_holds[0]["quantity"] == 2


# ---------------------------------------------------------------------------
# Commit
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_commit_inventory_success(db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=2)
    booking = await _create_booking(
        db_session, prop.id, date(2026, 5, 10), date(2026, 5, 12)
    )
    hold = InventoryHold(
        org_id=DEFAULT_ORG_ID,
        booking_id=booking.id,
        property_id=prop.id,
        room_type_id=rt.id,
        dates=[date(2026, 5, 10), date(2026, 5, 11)],
        status="active",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db_session.add(hold)
    await db_session.flush()
    await db_session.commit()

    svc = InventoryService(db_session)
    ok = await svc.commit_inventory(hold.id)
    assert ok is True

    await db_session.refresh(hold)
    assert hold.status == "committed"

    line_items = (
        await db_session.execute(
            select(BookingLineItem).where(BookingLineItem.booking_id == booking.id)
        )
    ).scalars().all()
    assert len(line_items) == 1
    assert line_items[0].item_type == "room"
    assert line_items[0].quantity == 1
    assert line_items[0].nights == 2


@pytest.mark.asyncio(loop_scope="session")
async def test_commit_inventory_expired_hold(db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=2)
    booking = await _create_booking(
        db_session, prop.id, date(2026, 5, 10), date(2026, 5, 11)
    )
    hold = InventoryHold(
        org_id=DEFAULT_ORG_ID,
        booking_id=booking.id,
        property_id=prop.id,
        room_type_id=rt.id,
        dates=[date(2026, 5, 10)],
        status="active",
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    db_session.add(hold)
    await db_session.flush()
    await db_session.commit()

    svc = InventoryService(db_session)
    with pytest.raises(InventoryError, match="Hold has expired"):
        await svc.commit_inventory(hold.id)


@pytest.mark.asyncio(loop_scope="session")
async def test_commit_inventory_concurrent_conflict(db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=1)
    booking_a = await _create_booking(
        db_session, prop.id, date(2026, 5, 10), date(2026, 5, 11)
    )
    booking_b = await _create_booking(
        db_session, prop.id, date(2026, 5, 10), date(2026, 5, 11)
    )
    hold_a = InventoryHold(
        org_id=DEFAULT_ORG_ID,
        booking_id=booking_a.id,
        property_id=prop.id,
        room_type_id=rt.id,
        dates=[date(2026, 5, 10)],
        status="active",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    hold_b = InventoryHold(
        org_id=DEFAULT_ORG_ID,
        booking_id=booking_b.id,
        property_id=prop.id,
        room_type_id=rt.id,
        dates=[date(2026, 5, 10)],
        status="committed",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db_session.add(hold_a)
    db_session.add(hold_b)
    await db_session.flush()
    await db_session.commit()

    svc = InventoryService(db_session)
    with pytest.raises(ConflictError, match="no longer available"):
        await svc.commit_inventory(hold_a.id)


@pytest.mark.asyncio(loop_scope="session")
async def test_commit_inventory_with_addon_holds(db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)
    addon = AddOn(
        org_id=DEFAULT_ORG_ID,
        property_id=prop.id,
        name="Spa",
        type=AddOnType.day,
        default_capacity=0,
        unit_price=100.00,
    )
    db_session.add(addon)
    await db_session.flush()

    cap = AddOnCapacity(
        add_on_id=addon.id,
        date=date(2026, 5, 10),
        total_capacity=5,
        available_capacity=5,
    )
    db_session.add(cap)
    await db_session.flush()

    booking = await _create_booking(
        db_session, prop.id, date(2026, 5, 10), date(2026, 5, 11)
    )
    hold = InventoryHold(
        org_id=DEFAULT_ORG_ID,
        booking_id=booking.id,
        property_id=prop.id,
        room_type_id=rt.id,
        dates=[date(2026, 5, 10)],
        add_on_holds=[
            {"add_on_id": str(addon.id), "date": "2026-05-10", "quantity": 2}
        ],
        status="active",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db_session.add(hold)
    await db_session.flush()
    await db_session.commit()

    svc = InventoryService(db_session)
    ok = await svc.commit_inventory(hold.id)
    assert ok is True

    await db_session.refresh(cap)
    assert cap.available_capacity == 3

    line_items = (
        await db_session.execute(
            select(BookingLineItem).where(BookingLineItem.booking_id == booking.id)
        )
    ).scalars().all()
    assert len(line_items) == 2
    addon_li = [li for li in line_items if li.item_type == "add_on"][0]
    assert addon_li.quantity == 2
    assert addon_li.total_price == Decimal("200.00")


# ---------------------------------------------------------------------------
# Release
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_release_inventory_success(db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=1)
    booking = await _create_booking(
        db_session, prop.id, date(2026, 5, 10), date(2026, 5, 11)
    )
    hold = InventoryHold(
        org_id=DEFAULT_ORG_ID,
        booking_id=booking.id,
        property_id=prop.id,
        room_type_id=rt.id,
        dates=[date(2026, 5, 10)],
        status="active",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db_session.add(hold)
    await db_session.flush()
    await db_session.commit()

    svc = InventoryService(db_session)
    ok = await svc.release_inventory(hold.id)
    assert ok is True

    await db_session.refresh(hold)
    assert hold.status == "released"


@pytest.mark.asyncio(loop_scope="session")
async def test_release_inventory_with_addon_holds(db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=1)
    addon = AddOn(
        org_id=DEFAULT_ORG_ID,
        property_id=prop.id,
        name="Spa",
        type=AddOnType.day,
        default_capacity=0,
        unit_price=100.00,
    )
    db_session.add(addon)
    await db_session.flush()

    cap = AddOnCapacity(
        add_on_id=addon.id,
        date=date(2026, 5, 10),
        total_capacity=5,
        available_capacity=3,
    )
    db_session.add(cap)
    await db_session.flush()

    booking = await _create_booking(
        db_session, prop.id, date(2026, 5, 10), date(2026, 5, 11)
    )
    hold = InventoryHold(
        org_id=DEFAULT_ORG_ID,
        booking_id=booking.id,
        property_id=prop.id,
        room_type_id=rt.id,
        dates=[date(2026, 5, 10)],
        add_on_holds=[
            {"add_on_id": str(addon.id), "date": "2026-05-10", "quantity": 2}
        ],
        status="active",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db_session.add(hold)
    await db_session.flush()
    await db_session.commit()

    svc = InventoryService(db_session)
    ok = await svc.release_inventory(hold.id)
    assert ok is True

    await db_session.refresh(cap)
    assert cap.available_capacity == 5


@pytest.mark.asyncio(loop_scope="session")
async def test_release_inventory_redis_cleanup(db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id)
    await db_session.commit()

    fake_redis = FakeRedis()
    svc = InventoryService(db_session, redis=fake_redis)
    hold_id = await svc.hold_inventory(
        booking_id=uuid.uuid4(),
        property_id=prop.id,
        room_type_id=rt.id,
        dates=[date(2026, 5, 10)],
    )
    assert await fake_redis.get(f"hold:{hold_id}") is not None

    ok = await svc.release_inventory(hold_id)
    assert ok is True
    assert await fake_redis.get(f"hold:{hold_id}") is None


# ---------------------------------------------------------------------------
# Concurrent load
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_concurrent_commit_last_room(db_session: AsyncSession, postgres_url: str):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=1)
    await db_session.commit()

    booking = await _create_booking(
        db_session, prop.id, date(2026, 8, 1), date(2026, 8, 2)
    )
    hold = InventoryHold(
        org_id=DEFAULT_ORG_ID,
        booking_id=booking.id,
        property_id=prop.id,
        room_type_id=rt.id,
        dates=[date(2026, 8, 1)],
        status="active",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db_session.add(hold)
    await db_session.flush()
    await db_session.commit()

    async_url = postgres_url.replace("postgresql+psycopg://", "postgresql+asyncpg://")
    engine = create_async_engine(
        async_url, pool_size=20, max_overflow=80, future=True
    )
    session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async def _commit_hold():
        async with session_maker() as session:
            svc = InventoryService(session)
            try:
                return await svc.commit_inventory(hold.id)
            except Exception:
                return False

    # Use 50 concurrent tasks to stay within default Postgres connection limits
    # while still exercising the serializable locking path.
    tasks = [_commit_hold() for _ in range(50)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    successes = [r for r in results if r is True]
    assert len(successes) == 1

    await engine.dispose()

    await db_session.refresh(hold)
    assert hold.status == "committed"
