import time as time_mod
import uuid
from datetime import date, datetime, time, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis_client
from app.main import app
from app.models.add_on import AddOn, AddOnType
from app.models.add_on_capacity import AddOnCapacity
from app.models.inventory_hold import InventoryHold
from app.models.property import Property
from app.models.room_type import RoomType

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def _create_property(session: AsyncSession) -> Property:
    prop = Property(org_id=DEFAULT_ORG_ID, name="Test Hotel")
    session.add(prop)
    await session.flush()
    await session.refresh(prop)
    return prop


async def _create_room_type(session: AsyncSession, property_id: uuid.UUID) -> RoomType:
    rt = RoomType(
        org_id=DEFAULT_ORG_ID,
        property_id=property_id,
        name="Deluxe",
        count=5,
        base_capacity=2,
        max_capacity=3,
        default_rate=100.00,
    )
    session.add(rt)
    await session.flush()
    await session.refresh(rt)
    return rt


async def _create_add_on(
    session: AsyncSession,
    property_id: uuid.UUID,
    add_on_type: AddOnType,
    default_capacity: int = 10,
) -> AddOn:
    addon = AddOn(
        org_id=DEFAULT_ORG_ID,
        property_id=property_id,
        name=f"Test {add_on_type.value}",
        type=add_on_type,
        default_capacity=default_capacity,
        unit_price=50.00,
    )
    session.add(addon)
    await session.flush()
    await session.refresh(addon)
    return addon


async def _create_add_on_capacity(
    session: AsyncSession,
    add_on_id: uuid.UUID,
    query_date: date,
    slot_time: time | None = None,
    total_capacity: int = 5,
) -> AddOnCapacity:
    cap = AddOnCapacity(
        add_on_id=add_on_id,
        date=query_date,
        slot_time=slot_time,
        total_capacity=total_capacity,
        available_capacity=total_capacity,
    )
    session.add(cap)
    await session.flush()
    await session.refresh(cap)
    return cap


@pytest.mark.asyncio(loop_scope="session")
async def test_addon_availability_slot_no_bookings(client: AsyncClient, db_session: AsyncSession):
    prop = await _create_property(db_session)
    addon = await _create_add_on(db_session, prop.id, AddOnType.slot)
    await _create_add_on_capacity(db_session, addon.id, date(2026, 5, 1), time(9, 0), total_capacity=5)

    response = await client.get(
        "/api/v1/availability/addons",
        params={"add_on_id": str(addon.id), "date": "2026-05-01"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["date"] == "2026-05-01"
    assert data[0]["slot_time"] == "09:00:00"
    assert data[0]["available_capacity"] == 5
    assert data[0]["total_capacity"] == 5
    assert data[0]["booked_count"] == 0
    assert data[0]["held_count"] == 0


@pytest.mark.asyncio(loop_scope="session")
async def test_addon_availability_day_no_bookings(client: AsyncClient, db_session: AsyncSession):
    prop = await _create_property(db_session)
    addon = await _create_add_on(db_session, prop.id, AddOnType.day)
    await _create_add_on_capacity(db_session, addon.id, date(2026, 5, 1), None, total_capacity=10)

    response = await client.get(
        "/api/v1/availability/addons",
        params={"add_on_id": str(addon.id), "date": "2026-05-01"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["date"] == "2026-05-01"
    assert data[0].get("slot_time") is None
    assert data[0]["available_capacity"] == 10
    assert data[0]["total_capacity"] == 10


@pytest.mark.asyncio(loop_scope="session")
async def test_addon_availability_package_instance(client: AsyncClient, db_session: AsyncSession):
    prop = await _create_property(db_session)
    addon = await _create_add_on(db_session, prop.id, AddOnType.package_instance, default_capacity=20)

    response = await client.get(
        "/api/v1/availability/addons",
        params={"add_on_id": str(addon.id), "date": "2026-05-01"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["date"] == "2026-05-01"
    assert data[0]["available_capacity"] == 20
    assert data[0]["total_capacity"] == 20


@pytest.mark.asyncio(loop_scope="session")
async def test_addon_availability_with_confirmed_booking(client: AsyncClient, db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id)
    addon = await _create_add_on(db_session, prop.id, AddOnType.slot)
    await _create_add_on_capacity(db_session, addon.id, date(2026, 5, 1), time(9, 0), total_capacity=5)

    hold = InventoryHold(
        org_id=DEFAULT_ORG_ID,
        booking_id=uuid.uuid4(),
        property_id=prop.id,
        room_type_id=rt.id,
        dates=[date(2026, 5, 1)],
        status="committed",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        add_on_holds=[{"add_on_id": str(addon.id), "date": "2026-05-01", "slot_time": "09:00:00", "quantity": 2}],
    )
    db_session.add(hold)
    await db_session.flush()

    response = await client.get(
        "/api/v1/availability/addons",
        params={"add_on_id": str(addon.id), "date": "2026-05-01", "slot_time": "09:00:00"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["booked_count"] == 2
    assert data[0]["available_capacity"] == 3


@pytest.mark.asyncio(loop_scope="session")
async def test_addon_availability_with_active_hold(client: AsyncClient, db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id)
    addon = await _create_add_on(db_session, prop.id, AddOnType.day)
    await _create_add_on_capacity(db_session, addon.id, date(2026, 5, 1), None, total_capacity=10)

    hold = InventoryHold(
        org_id=DEFAULT_ORG_ID,
        booking_id=uuid.uuid4(),
        property_id=prop.id,
        room_type_id=rt.id,
        dates=[date(2026, 5, 1)],
        status="active",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        add_on_holds=[{"add_on_id": str(addon.id), "date": "2026-05-01", "quantity": 3}],
    )
    db_session.add(hold)
    await db_session.flush()

    response = await client.get(
        "/api/v1/availability/addons",
        params={"add_on_id": str(addon.id), "date": "2026-05-01"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["held_count"] == 3
    assert data[0]["available_capacity"] == 7


@pytest.mark.asyncio(loop_scope="session")
async def test_addon_availability_expired_hold_ignored(client: AsyncClient, db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id)
    addon = await _create_add_on(db_session, prop.id, AddOnType.day)
    await _create_add_on_capacity(db_session, addon.id, date(2026, 5, 1), None, total_capacity=10)

    hold = InventoryHold(
        org_id=DEFAULT_ORG_ID,
        booking_id=uuid.uuid4(),
        property_id=prop.id,
        room_type_id=rt.id,
        dates=[date(2026, 5, 1)],
        status="active",
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        add_on_holds=[{"add_on_id": str(addon.id), "date": "2026-05-01", "quantity": 5}],
    )
    db_session.add(hold)
    await db_session.flush()

    response = await client.get(
        "/api/v1/availability/addons",
        params={"add_on_id": str(addon.id), "date": "2026-05-01"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data[0]["held_count"] == 0
    assert data[0]["available_capacity"] == 10


@pytest.mark.asyncio(loop_scope="session")
async def test_addon_availability_cache_hit(client: AsyncClient, db_session: AsyncSession):
    prop = await _create_property(db_session)
    addon = await _create_add_on(db_session, prop.id, AddOnType.day)
    await _create_add_on_capacity(db_session, addon.id, date(2026, 6, 1), None, total_capacity=10)

    start = time_mod.perf_counter()
    response1 = await client.get(
        "/api/v1/availability/addons",
        params={"add_on_id": str(addon.id), "date": "2026-06-01"},
    )
    elapsed_first = time_mod.perf_counter() - start
    assert response1.status_code == 200

    start = time_mod.perf_counter()
    response2 = await client.get(
        "/api/v1/availability/addons",
        params={"add_on_id": str(addon.id), "date": "2026-06-01"},
    )
    elapsed_second = time_mod.perf_counter() - start
    assert response2.status_code == 200

    assert response1.json() == response2.json()
    assert elapsed_second < elapsed_first

    fake_redis = await app.dependency_overrides[get_redis_client]()
    cache_key = f"avail:addon:{addon.id}:2026-06-01:all"
    cached = await fake_redis.get(cache_key)
    assert cached is not None


@pytest.mark.asyncio(loop_scope="session")
async def test_addon_availability_range(client: AsyncClient, db_session: AsyncSession):
    prop = await _create_property(db_session)
    addon = await _create_add_on(db_session, prop.id, AddOnType.day)
    await _create_add_on_capacity(db_session, addon.id, date(2026, 5, 1), None, total_capacity=10)
    await _create_add_on_capacity(db_session, addon.id, date(2026, 5, 2), None, total_capacity=10)

    response = await client.get(
        "/api/v1/availability/addons/range",
        params={"add_on_id": str(addon.id), "start_date": "2026-05-01", "end_date": "2026-05-02"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["date"] == "2026-05-01"
    assert data[1]["date"] == "2026-05-02"


@pytest.mark.asyncio(loop_scope="session")
async def test_addon_availability_invalid_dates(client: AsyncClient, db_session: AsyncSession):
    prop = await _create_property(db_session)
    addon = await _create_add_on(db_session, prop.id, AddOnType.day)

    response = await client.get(
        "/api/v1/availability/addons/range",
        params={"add_on_id": str(addon.id), "start_date": "2026-05-03", "end_date": "2026-05-01"},
    )
    assert response.status_code == 422
