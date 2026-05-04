import time
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis_client
from app.main import app
from app.models.inventory_hold import InventoryHold
from app.models.package import Package, PackageComposition
from app.models.property import Property
from app.models.promo_code import PromoCode
from app.models.room_type import RoomType
from app.repositories.pricing import PromoCodeRepository
from app.schemas.search import SearchRequest
from app.services.search_service import SearchService

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def _create_property(session: AsyncSession) -> Property:
    prop = Property(
        org_id=DEFAULT_ORG_ID,
        name="Search Test Hotel",
        address="123 Search St",
    )
    session.add(prop)
    await session.flush()
    await session.refresh(prop)
    return prop


async def _create_room_type(
    session: AsyncSession,
    property_id: uuid.UUID,
    count: int = 5,
    default_rate: Decimal = Decimal("5000.00"),
) -> RoomType:
    rt = RoomType(
        org_id=DEFAULT_ORG_ID,
        property_id=property_id,
        name="Deluxe",
        count=count,
        base_capacity=2,
        max_capacity=3,
        default_rate=default_rate,
    )
    session.add(rt)
    await session.flush()
    await session.refresh(rt)
    return rt


async def _create_package(
    session: AsyncSession,
    property_id: uuid.UUID,
    room_type_id: uuid.UUID,
) -> Package:
    pkg = Package(
        org_id=DEFAULT_ORG_ID,
        property_id=property_id,
        name="Weekend Special",
        description="A great package",
        status="active",
        base_price=Decimal("15000.00"),
        max_occupancy=4,
    )
    session.add(pkg)
    await session.flush()
    await session.refresh(pkg)

    comp = PackageComposition(
        org_id=DEFAULT_ORG_ID,
        package_id=pkg.id,
        room_type_id=room_type_id,
        quantity=1,
        nights=2,
    )
    session.add(comp)
    await session.flush()
    return pkg


async def _create_promo_code(
    session: AsyncSession,
    code: str,
    discount_type: str,
    discount_value: Decimal,
) -> PromoCode:
    repo = PromoCodeRepository(session, DEFAULT_ORG_ID)
    return await repo.create(
        {
            "code": code,
            "discount_type": discount_type,
            "discount_value": discount_value,
        }
    )


@pytest.mark.asyncio
async def test_search_with_available_rooms(client: AsyncClient, db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id)

    response = await client.post(
        "/api/v1/search/",
        json={
            "location": "Search Test",
            "check_in": str(date.today() + timedelta(days=10)),
            "check_out": str(date.today() + timedelta(days=12)),
            "guests": 2,
        },
    )
    assert response.status_code == 200
    data = response.json()
    room_results = [r for r in data["results"] if r["type"] == "room"]
    assert any(r["id"] == str(rt.id) for r in room_results)
    item = next(r for r in room_results if r["id"] == str(rt.id))
    assert item["name"] == "Deluxe"
    assert item["available"] is True
    assert float(item["price_breakdown"]["subtotal"]) > 0


@pytest.mark.asyncio
async def test_search_with_sold_out_rooms_filtered_out(
    client: AsyncClient, db_session: AsyncSession
):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=1)

    hold = InventoryHold(
        org_id=DEFAULT_ORG_ID,
        booking_id=uuid.uuid4(),
        property_id=prop.id,
        room_type_id=rt.id,
        dates=[date.today() + timedelta(days=10), date.today() + timedelta(days=11)],
        status="committed",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db_session.add(hold)
    await db_session.flush()

    response = await client.post(
        "/api/v1/search/",
        json={
            "location": "Search Test",
            "check_in": str(date.today() + timedelta(days=10)),
            "check_out": str(date.today() + timedelta(days=12)),
            "guests": 2,
        },
    )
    assert response.status_code == 200
    data = response.json()
    room_results = [r for r in data["results"] if r["type"] == "room"]
    assert not any(r["id"] == str(rt.id) for r in room_results)


@pytest.mark.asyncio
async def test_search_with_packages(client: AsyncClient, db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id)
    pkg = await _create_package(db_session, prop.id, rt.id)

    response = await client.post(
        "/api/v1/search/",
        json={
            "location": "Search Test",
            "check_in": str(date.today() + timedelta(days=10)),
            "check_out": str(date.today() + timedelta(days=12)),
            "guests": 2,
        },
    )
    assert response.status_code == 200
    data = response.json()
    pkg_results = [r for r in data["results"] if r["type"] == "package"]
    assert any(r["id"] == str(pkg.id) for r in pkg_results)
    item = next(r for r in pkg_results if r["id"] == str(pkg.id))
    assert item["name"] == "Weekend Special"
    assert float(item["price_breakdown"]["subtotal"]) > 0


@pytest.mark.asyncio
async def test_search_with_promo_code_applied(
    client: AsyncClient, db_session: AsyncSession
):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, default_rate=Decimal("5000.00"))
    await _create_promo_code(db_session, "SEARCH10", "percentage", Decimal("10.00"))

    response = await client.post(
        "/api/v1/search/",
        json={
            "location": "Search Test",
            "check_in": str(date.today() + timedelta(days=10)),
            "check_out": str(date.today() + timedelta(days=12)),
            "guests": 2,
            "promo_code": "SEARCH10",
        },
    )
    assert response.status_code == 200
    data = response.json()
    room_results = [r for r in data["results"] if r["type"] == "room"]
    item = next(r for r in room_results if r["id"] == str(rt.id))
    # 2 nights * 5000 = 10000 - 10% = 9000
    assert float(item["price_breakdown"]["subtotal"]) == 10000.0
    assert float(item["price_breakdown"]["discount_amount"]) == 1000.0


@pytest.mark.asyncio
async def test_search_cache_hit(client: AsyncClient, db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id)

    payload = {
        "location": "Search Test",
        "check_in": str(date.today() + timedelta(days=20)),
        "check_out": str(date.today() + timedelta(days=22)),
        "guests": 2,
    }

    start = time.perf_counter()
    response1 = await client.post("/api/v1/search/", json=payload)
    elapsed_first = time.perf_counter() - start
    assert response1.status_code == 200

    start = time.perf_counter()
    response2 = await client.post("/api/v1/search/", json=payload)
    elapsed_second = time.perf_counter() - start
    assert response2.status_code == 200

    assert response1.json() == response2.json()
    assert elapsed_second < elapsed_first

    # Verify exact cache key exists in fake redis
    fake_redis = await app.dependency_overrides[get_redis_client]()
    req = SearchRequest(**payload)
    cache_key = SearchService._cache_key(DEFAULT_ORG_ID, req)
    cached = await fake_redis.get(cache_key)
    assert cached is not None


@pytest.mark.asyncio
async def test_search_invalid_date_range(client: AsyncClient, db_session: AsyncSession):
    prop = await _create_property(db_session)
    await _create_room_type(db_session, prop.id)

    response = await client.post(
        "/api/v1/search/",
        json={
            "location": "Search Test",
            "check_in": str(date.today() + timedelta(days=12)),
            "check_out": str(date.today() + timedelta(days=10)),
            "guests": 2,
        },
    )
    assert response.status_code == 422
