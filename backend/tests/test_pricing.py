import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.property import Property
from app.models.room_type import RoomType
from app.models.package import Package
from app.models.rate_plan import RatePlan
from app.models.seasonal_calendar import SeasonalCalendar
from app.models.promo_code import PromoCode
from app.repositories.property import PropertyRepository
from app.repositories.room_type import RoomTypeRepository
from app.repositories.package import PackageRepository
from app.repositories.pricing import RatePlanRepository, SeasonalCalendarRepository, PromoCodeRepository
from app.services.pricing_service import PricingService

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def _create_property(db_session: AsyncSession) -> Property:
    repo = PropertyRepository(db_session, DEFAULT_ORG_ID)
    return await repo.create({"name": "Pricing Test Hotel"})


async def _create_room_type(db_session: AsyncSession, property_id: uuid.UUID, default_rate: Decimal = Decimal("5000.00")) -> RoomType:
    repo = RoomTypeRepository(db_session, DEFAULT_ORG_ID)
    return await repo.create({
        "property_id": property_id,
        "name": "Deluxe Room",
        "count": 5,
        "default_rate": default_rate,
    })


async def _create_package(db_session: AsyncSession, property_id: uuid.UUID, base_price: Decimal = Decimal("15000.00"), dynamic_pricing_rules: dict | None = None) -> Package:
    repo = PackageRepository(db_session, DEFAULT_ORG_ID)
    return await repo.create({
        "property_id": property_id,
        "name": "Weekend Package",
        "base_price": base_price,
        "dynamic_pricing_rules": dynamic_pricing_rules or {},
        "status": "active",
    })


async def _create_rate_plan(db_session: AsyncSession, code: str, discount_type: str, discount_value: Decimal, min_nights: int | None = None, max_nights: int | None = None) -> RatePlan:
    repo = RatePlanRepository(db_session, DEFAULT_ORG_ID)
    return await repo.create({
        "name": code,
        "code": code,
        "discount_type": discount_type,
        "discount_value": discount_value,
        "min_nights": min_nights,
        "max_nights": max_nights,
    })


async def _create_seasonal_calendar(db_session: AsyncSession, name: str, start_date: date, end_date: date, multiplier: Decimal) -> SeasonalCalendar:
    repo = SeasonalCalendarRepository(db_session, DEFAULT_ORG_ID)
    return await repo.create({
        "name": name,
        "start_date": start_date,
        "end_date": end_date,
        "multiplier": multiplier,
    })


async def _create_promo_code(db_session: AsyncSession, code: str, discount_type: str, discount_value: Decimal, max_uses: int | None = None, valid_from: date | None = None, valid_to: date | None = None, applicable_types: list[str] | None = None) -> PromoCode:
    repo = PromoCodeRepository(db_session, DEFAULT_ORG_ID)
    return await repo.create({
        "code": code,
        "discount_type": discount_type,
        "discount_value": discount_value,
        "max_uses": max_uses,
        "valid_from": valid_from,
        "valid_to": valid_to,
        "applicable_booking_types": applicable_types,
    })


# ---------------------------------------------------------------------------
# Room pricing tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_bar_rate_plan_no_discount(db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, Decimal("5000.00"))
    await _create_rate_plan(db_session, "BAR", "percentage", Decimal("0.00"))

    service = PricingService(db_session)
    check_in = date.today() + timedelta(days=10)
    check_out = check_in + timedelta(days=2)
    result = await service.calculate_room_price(
        rt.id, check_in, check_out, rate_plan_code="BAR"
    )

    # 2 nights * 5000 = 10000
    assert result.subtotal == Decimal("10000.00")
    assert result.discount_amount == Decimal("0.00")
    assert result.taxable_amount == Decimal("10000.00")
    assert result.tax_amount == Decimal("1200.00")
    assert result.total_amount == Decimal("11200.00")
    assert result.channel_markup_amount == Decimal("0.00")


@pytest.mark.asyncio(loop_scope="session")
async def test_non_refundable_rate_plan(db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, Decimal("5000.00"))
    await _create_rate_plan(db_session, "NONREF", "percentage", Decimal("10.00"))

    service = PricingService(db_session)
    check_in = date.today() + timedelta(days=10)
    check_out = check_in + timedelta(days=2)
    result = await service.calculate_room_price(
        rt.id, check_in, check_out, rate_plan_code="NONREF"
    )

    # 2 nights * 5000 = 10000, -10% = 9000
    assert result.subtotal == Decimal("9000.00")
    assert result.discount_amount == Decimal("1000.00")
    assert result.taxable_amount == Decimal("9000.00")
    assert result.tax_amount == Decimal("1080.00")
    assert result.total_amount == Decimal("10080.00")


@pytest.mark.asyncio(loop_scope="session")
async def test_long_stay_rate_plan_applies(db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, Decimal("5000.00"))
    await _create_rate_plan(db_session, "LONGSTAY", "percentage", Decimal("15.00"), min_nights=7)

    service = PricingService(db_session)
    check_in = date.today() + timedelta(days=10)
    check_out = check_in + timedelta(days=7)
    result = await service.calculate_room_price(
        rt.id, check_in, check_out, rate_plan_code="LONGSTAY"
    )

    # 7 nights * 5000 = 35000, -15% = 29750
    assert result.subtotal == Decimal("29750.00")
    assert result.discount_amount == Decimal("5250.00")
    assert result.taxable_amount == Decimal("29750.00")
    assert result.tax_amount == Decimal("3570.00")
    assert result.total_amount == Decimal("33320.00")


@pytest.mark.asyncio(loop_scope="session")
async def test_long_stay_rate_plan_not_applicable(db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, Decimal("5000.00"))
    await _create_rate_plan(db_session, "LONGSTAY", "percentage", Decimal("15.00"), min_nights=7)

    service = PricingService(db_session)
    check_in = date.today() + timedelta(days=10)
    check_out = check_in + timedelta(days=3)
    result = await service.calculate_room_price(
        rt.id, check_in, check_out, rate_plan_code="LONGSTAY"
    )

    # 3 nights * 5000 = 15000 (no discount because min_nights=7)
    assert result.subtotal == Decimal("15000.00")
    assert result.discount_amount == Decimal("0.00")


@pytest.mark.asyncio(loop_scope="session")
async def test_peak_season_multiplier(db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, Decimal("5000.00"))

    check_in = date.today() + timedelta(days=10)
    check_out = check_in + timedelta(days=2)
    await _create_seasonal_calendar(db_session, "Peak", check_in, check_out - timedelta(days=1), Decimal("1.20"))

    service = PricingService(db_session)
    result = await service.calculate_room_price(rt.id, check_in, check_out)

    # 2 nights * 5000 * 1.2 = 12000
    assert result.subtotal == Decimal("12000.00")
    assert result.taxable_amount == Decimal("12000.00")
    assert result.tax_amount == Decimal("1440.00")
    assert result.total_amount == Decimal("13440.00")


@pytest.mark.asyncio(loop_scope="session")
async def test_off_season_no_multiplier(db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, Decimal("5000.00"))

    check_in = date.today() + timedelta(days=10)
    check_out = check_in + timedelta(days=2)
    # No seasonal calendar created

    service = PricingService(db_session)
    result = await service.calculate_room_price(rt.id, check_in, check_out)

    assert result.subtotal == Decimal("10000.00")
    assert result.taxable_amount == Decimal("10000.00")


@pytest.mark.asyncio(loop_scope="session")
async def test_overlapping_seasons_highest_wins(db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, Decimal("5000.00"))

    check_in = date.today() + timedelta(days=10)
    check_out = check_in + timedelta(days=2)
    await _create_seasonal_calendar(db_session, "Low", check_in, check_out - timedelta(days=1), Decimal("1.10"))
    await _create_seasonal_calendar(db_session, "High", check_in, check_out - timedelta(days=1), Decimal("1.20"))

    service = PricingService(db_session)
    result = await service.calculate_room_price(rt.id, check_in, check_out)

    # highest multiplier 1.20 wins
    assert result.subtotal == Decimal("12000.00")


@pytest.mark.asyncio(loop_scope="session")
async def test_promo_code_percentage_discount(db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, Decimal("5000.00"))
    await _create_promo_code(db_session, "SAVE10", "percentage", Decimal("10.00"))

    service = PricingService(db_session)
    check_in = date.today() + timedelta(days=10)
    check_out = check_in + timedelta(days=2)
    result = await service.calculate_room_price(
        rt.id, check_in, check_out, promo_code="SAVE10"
    )

    # 10000 - 10% = 9000
    assert result.subtotal == Decimal("10000.00")
    assert result.discount_amount == Decimal("1000.00")
    assert result.taxable_amount == Decimal("9000.00")
    assert result.tax_amount == Decimal("1080.00")
    assert result.total_amount == Decimal("10080.00")


@pytest.mark.asyncio(loop_scope="session")
async def test_promo_code_fixed_discount(db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, Decimal("5000.00"))
    await _create_promo_code(db_session, "FLAT500", "fixed", Decimal("500.00"))

    service = PricingService(db_session)
    check_in = date.today() + timedelta(days=10)
    check_out = check_in + timedelta(days=2)
    result = await service.calculate_room_price(
        rt.id, check_in, check_out, promo_code="FLAT500"
    )

    assert result.subtotal == Decimal("10000.00")
    assert result.discount_amount == Decimal("500.00")
    assert result.taxable_amount == Decimal("9500.00")
    assert result.tax_amount == Decimal("1140.00")
    assert result.total_amount == Decimal("10640.00")


@pytest.mark.asyncio(loop_scope="session")
async def test_invalid_expired_promo_code(db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, Decimal("5000.00"))
    await _create_promo_code(
        db_session, "EXPIRED", "percentage", Decimal("50.00"),
        valid_from=date.today() - timedelta(days=10),
        valid_to=date.today() - timedelta(days=1),
    )

    service = PricingService(db_session)
    check_in = date.today() + timedelta(days=10)
    check_out = check_in + timedelta(days=2)
    result = await service.calculate_room_price(
        rt.id, check_in, check_out, promo_code="EXPIRED"
    )

    # promo expired so no discount
    assert result.subtotal == Decimal("10000.00")
    assert result.discount_amount == Decimal("0.00")


@pytest.mark.asyncio(loop_scope="session")
async def test_channel_markup_ota(db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, Decimal("5000.00"))

    service = PricingService(db_session)
    check_in = date.today() + timedelta(days=10)
    check_out = check_in + timedelta(days=2)
    result = await service.calculate_room_price(
        rt.id, check_in, check_out, channel_source="gmail_airbnb"
    )

    # subtotal 10000, tax 1200, base_with_tax = 11200, +18% = 13216
    assert result.subtotal == Decimal("10000.00")
    assert result.tax_amount == Decimal("1200.00")
    assert result.channel_markup_amount == Decimal("2016.00")
    assert result.total_amount == Decimal("13216.00")


@pytest.mark.asyncio(loop_scope="session")
async def test_channel_markup_direct_no_markup(db_session: AsyncSession):
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, Decimal("5000.00"))

    service = PricingService(db_session)
    check_in = date.today() + timedelta(days=10)
    check_out = check_in + timedelta(days=2)
    result = await service.calculate_room_price(
        rt.id, check_in, check_out, channel_source="direct"
    )

    assert result.channel_markup_amount == Decimal("0.00")
    assert result.total_amount == Decimal("11200.00")


# ---------------------------------------------------------------------------
# Package pricing tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_package_occupancy_scaling(db_session: AsyncSession):
    prop = await _create_property(db_session)
    pkg = await _create_package(db_session, prop.id, Decimal("10000.00"), dynamic_pricing_rules={
        "occupancy_scaling": {
            "base_occupancy": 2,
            "extra_guest_charge": 500.00,
        }
    })

    service = PricingService(db_session)
    check_in = date.today() + timedelta(days=10)
    check_out = check_in + timedelta(days=2)
    result = await service.calculate_package_price(
        pkg.id, check_in, check_out, guests=4
    )

    # base 10000 + 2 extra guests * 500 * 2 nights = 12000
    assert result.subtotal == Decimal("12000.00")


@pytest.mark.asyncio(loop_scope="session")
async def test_package_early_bird_discount(db_session: AsyncSession):
    prop = await _create_property(db_session)
    pkg = await _create_package(db_session, prop.id, Decimal("10000.00"), dynamic_pricing_rules={
        "early_bird": {
            "min_days_before": 30,
            "discount_percentage": 15.0,
        }
    })

    service = PricingService(db_session)
    check_in = date.today() + timedelta(days=60)
    check_out = check_in + timedelta(days=2)
    result = await service.calculate_package_price(
        pkg.id, check_in, check_out
    )

    # 10000 - 15% = 8500
    assert result.subtotal == Decimal("8500.00")
    assert result.discount_amount == Decimal("1500.00")
    assert result.taxable_amount == Decimal("8500.00")
    assert result.tax_amount == Decimal("1020.00")
    assert result.total_amount == Decimal("9520.00")


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_api_calculate_room_price(client: AsyncClient):
    prop_resp = await client.post("/api/v1/properties/", json={"name": "API Pricing Hotel"})
    assert prop_resp.status_code == 201
    prop_id = prop_resp.json()["id"]

    rt_resp = await client.post(f"/api/v1/properties/{prop_id}/room-types", json={
        "name": "Standard",
        "count": 5,
        "default_rate": "4000.00",
    })
    assert rt_resp.status_code == 201
    rt_id = rt_resp.json()["id"]

    check_in = date.today() + timedelta(days=10)
    check_out = check_in + timedelta(days=2)
    resp = await client.get(
        f"/api/v1/pricing/calculate-room?room_type_id={rt_id}"
        f"&check_in={check_in}&check_out={check_out}"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(data["subtotal"]) == Decimal("8000.00")
    assert Decimal(data["tax_amount"]) == Decimal("960.00")
    assert Decimal(data["total_amount"]) == Decimal("8960.00")


@pytest.mark.asyncio(loop_scope="session")
async def test_api_rate_plan_crud(client: AsyncClient):
    resp = await client.post("/api/v1/pricing/rate-plans/", json={
        "name": "Test BAR",
        "code": "TESTBAR",
        "discount_type": "percentage",
        "discount_value": "0.00",
    })
    assert resp.status_code == 201
    data = resp.json()
    rp_id = data["id"]
    assert data["code"] == "TESTBAR"

    resp = await client.get(f"/api/v1/pricing/rate-plans/{rp_id}")
    assert resp.status_code == 200
    assert resp.json()["code"] == "TESTBAR"

    resp = await client.patch(f"/api/v1/pricing/rate-plans/{rp_id}", json={
        "discount_value": "10.00",
    })
    assert resp.status_code == 200
    assert Decimal(resp.json()["discount_value"]) == Decimal("10.00")

    resp = await client.delete(f"/api/v1/pricing/rate-plans/{rp_id}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/v1/pricing/rate-plans/{rp_id}")
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


@pytest.mark.asyncio(loop_scope="session")
async def test_api_seasonal_calendar_crud(client: AsyncClient):
    start = date.today() + timedelta(days=5)
    end = start + timedelta(days=5)
    resp = await client.post("/api/v1/pricing/seasonal-calendars/", json={
        "name": "Summer",
        "start_date": str(start),
        "end_date": str(end),
        "multiplier": "1.25",
    })
    assert resp.status_code == 201
    data = resp.json()
    sc_id = data["id"]
    assert Decimal(data["multiplier"]) == Decimal("1.25")

    resp = await client.get(f"/api/v1/pricing/seasonal-calendars/{sc_id}")
    assert resp.status_code == 200

    resp = await client.patch(f"/api/v1/pricing/seasonal-calendars/{sc_id}", json={
        "multiplier": "1.30",
    })
    assert resp.status_code == 200
    assert Decimal(resp.json()["multiplier"]) == Decimal("1.30")

    resp = await client.delete(f"/api/v1/pricing/seasonal-calendars/{sc_id}")
    assert resp.status_code == 204


@pytest.mark.asyncio(loop_scope="session")
async def test_api_promo_code_crud(client: AsyncClient):
    valid_from = date.today()
    valid_to = valid_from + timedelta(days=30)
    resp = await client.post("/api/v1/pricing/promo-codes/", json={
        "code": "WELCOME20",
        "discount_type": "percentage",
        "discount_value": "20.00",
        "max_uses": 100,
        "valid_from": str(valid_from),
        "valid_to": str(valid_to),
        "applicable_booking_types": ["room", "package"],
    })
    assert resp.status_code == 201
    data = resp.json()
    pc_id = data["id"]
    assert data["code"] == "WELCOME20"

    resp = await client.get(f"/api/v1/pricing/promo-codes/{pc_id}")
    assert resp.status_code == 200

    resp = await client.patch(f"/api/v1/pricing/promo-codes/{pc_id}", json={
        "used_count": 5,
    })
    assert resp.status_code == 200
    assert resp.json()["used_count"] == 5

    resp = await client.delete(f"/api/v1/pricing/promo-codes/{pc_id}")
    assert resp.status_code == 204
