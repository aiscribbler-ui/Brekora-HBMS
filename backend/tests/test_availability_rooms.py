import time
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis_client
from app.main import app
from app.models.inventory_hold import InventoryHold
from app.models.property import Property
from app.models.room_type import RoomType

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


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


@pytest.mark.asyncio
async def test_availability_no_bookings_or_holds(client: AsyncClient, db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)

    response = await client.get(
        "/api/v1/availability/rooms",
        params={
            "property_id": str(prop.id),
            "room_type_id": str(rt.id),
            "check_in": "2026-05-01",
            "check_out": "2026-05-03",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["date"] == "2026-05-01"
    assert data[0]["available_count"] == 5
    assert data[0]["total_count"] == 5
    assert data[0]["booked_count"] == 0
    assert data[0]["held_count"] == 0
    assert data[1]["date"] == "2026-05-02"
    assert data[1]["available_count"] == 5


@pytest.mark.asyncio
async def test_availability_with_confirmed_booking(client: AsyncClient, db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)

    hold = InventoryHold(
        org_id=DEFAULT_ORG_ID,
        booking_id=uuid.uuid4(),
        property_id=prop.id,
        room_type_id=rt.id,
        dates=[date(2026, 5, 1), date(2026, 5, 2)],
        status="committed",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db_session.add(hold)
    await db_session.flush()

    response = await client.get(
        "/api/v1/availability/rooms",
        params={
            "property_id": str(prop.id),
            "room_type_id": str(rt.id),
            "check_in": "2026-05-01",
            "check_out": "2026-05-03",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["available_count"] == 4
    assert data[0]["booked_count"] == 1
    assert data[0]["held_count"] == 0
    assert data[1]["available_count"] == 4


@pytest.mark.asyncio
async def test_availability_with_active_hold(client: AsyncClient, db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)

    hold = InventoryHold(
        org_id=DEFAULT_ORG_ID,
        booking_id=uuid.uuid4(),
        property_id=prop.id,
        room_type_id=rt.id,
        dates=[date(2026, 5, 1)],
        status="active",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db_session.add(hold)
    await db_session.flush()

    response = await client.get(
        "/api/v1/availability/rooms",
        params={
            "property_id": str(prop.id),
            "room_type_id": str(rt.id),
            "check_in": "2026-05-01",
            "check_out": "2026-05-02",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["available_count"] == 4
    assert data[0]["booked_count"] == 0
    assert data[0]["held_count"] == 1


@pytest.mark.asyncio
async def test_availability_expired_hold_ignored(client: AsyncClient, db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)

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

    response = await client.get(
        "/api/v1/availability/rooms",
        params={
            "property_id": str(prop.id),
            "room_type_id": str(rt.id),
            "check_in": "2026-05-01",
            "check_out": "2026-05-02",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data[0]["available_count"] == 5
    assert data[0]["held_count"] == 0


@pytest.mark.asyncio
async def test_availability_cancelled_booking_ignored(client: AsyncClient, db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)

    hold = InventoryHold(
        org_id=DEFAULT_ORG_ID,
        booking_id=uuid.uuid4(),
        property_id=prop.id,
        room_type_id=rt.id,
        dates=[date(2026, 5, 1)],
        status="cancelled",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db_session.add(hold)
    await db_session.flush()

    response = await client.get(
        "/api/v1/availability/rooms",
        params={
            "property_id": str(prop.id),
            "room_type_id": str(rt.id),
            "check_in": "2026-05-01",
            "check_out": "2026-05-02",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data[0]["available_count"] == 5
    assert data[0]["booked_count"] == 0


@pytest.mark.asyncio
async def test_availability_cache_hit(client: AsyncClient, db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)

    # First request
    start = time.perf_counter()
    response1 = await client.get(
        "/api/v1/availability/rooms",
        params={
            "property_id": str(prop.id),
            "room_type_id": str(rt.id),
            "check_in": "2026-06-01",
            "check_out": "2026-06-03",
        },
    )
    elapsed_first = time.perf_counter() - start
    assert response1.status_code == 200

    # Second request (should hit Redis cache)
    start = time.perf_counter()
    response2 = await client.get(
        "/api/v1/availability/rooms",
        params={
            "property_id": str(prop.id),
            "room_type_id": str(rt.id),
            "check_in": "2026-06-01",
            "check_out": "2026-06-03",
        },
    )
    elapsed_second = time.perf_counter() - start
    assert response2.status_code == 200

    assert response1.json() == response2.json()
    assert elapsed_second < elapsed_first

    # Verify cache key exists in fake redis
    fake_redis = await app.dependency_overrides[get_redis_client]()
    cache_key = (
        f"avail:rooms:{prop.id}:{rt.id}:2026-06-01:2026-06-03"
    )
    cached = await fake_redis.get(cache_key)
    assert cached is not None


@pytest.mark.asyncio
async def test_availability_invalid_dates(client: AsyncClient, db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id)

    response = await client.get(
        "/api/v1/availability/rooms",
        params={
            "property_id": str(prop.id),
            "room_type_id": str(rt.id),
            "check_in": "2026-05-03",
            "check_out": "2026-05-01",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_availability_nonexistent_room_type(client: AsyncClient):
    fake_id = uuid.uuid4()
    response = await client.get(
        "/api/v1/availability/rooms",
        params={
            "property_id": str(fake_id),
            "room_type_id": str(fake_id),
            "check_in": "2026-05-01",
            "check_out": "2026-05-02",
        },
    )
    assert response.status_code == 200
    assert response.json() == []
