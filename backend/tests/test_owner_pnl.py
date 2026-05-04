import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.db.session import get_db
from app.main import app
from app.models.booking import Booking, BookingStatus, SourceType
from app.models.property import Property
from app.models.role import Role
from app.models.system_config import SystemConfig
from app.models.user import User
from app.repositories.booking import BookingRepository
from app.repositories.property import PropertyRepository
from app.repositories.system_config import SystemConfigRepository
from app.repositories.user import UserRepository
from app.services.owner_service import OwnerService
from tests.conftest import FakeRedis

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def _create_property(db_session: AsyncSession, name: str = "Test Hotel") -> Property:
    repo = PropertyRepository(db_session, DEFAULT_ORG_ID)
    return await repo.create({"name": name})


async def _create_guest(db_session: AsyncSession) -> User:
    repo = UserRepository(db_session, DEFAULT_ORG_ID)
    return await repo.create(
        {
            "email": f"guest_{uuid.uuid4().hex}@example.com",
            "password_hash": "hash",
            "first_name": "Guest",
            "last_name": "User",
        }
    )


async def _create_booking(
    db_session: AsyncSession,
    property_id: uuid.UUID,
    check_in: date,
    gross_amount: Decimal,
    source_type: str = SourceType.direct.value,
    partner_attribution_id: str | None = None,
    status: str = BookingStatus.confirmed.value,
) -> Booking:
    guest = await _create_guest(db_session)
    repo = BookingRepository(db_session, DEFAULT_ORG_ID)
    return await repo.create_with_line_items(
        {
            "booking_type": "room",
            "property_id": property_id,
            "guest_id": guest.id,
            "check_in": check_in,
            "check_out": check_in + timedelta(days=2),
            "status": status,
            "gross_amount": gross_amount,
            "total_amount": gross_amount,
            "source_type": source_type,
            "partner_attribution_id": partner_attribution_id,
        },
        line_items=[
            {
                "item_type": "room",
                "item_id": uuid.uuid4(),
                "quantity": 1,
                "unit_price": gross_amount,
                "nights": 2,
                "total_price": gross_amount,
            }
        ],
    )


async def _create_user_with_role(
    db_session: AsyncSession, email: str, password: str, role_name: str
) -> User:
    result = await db_session.execute(
        select(Role).where(Role.name == role_name, Role.org_id == DEFAULT_ORG_ID)
    )
    role = result.scalar_one_or_none()

    repo = UserRepository(db_session, DEFAULT_ORG_ID)
    return await repo.create(
        {
            "email": email,
            "password_hash": get_password_hash(password),
            "first_name": "Test",
            "last_name": "User",
            "role_id": role.id if role else None,
        }
    )


async def _login(client: AsyncClient, email: str, password: str) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest_asyncio.fixture(loop_scope="function")
async def api_client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    fake_redis = FakeRedis()

    async def override_get_redis():
        return fake_redis

    from app.core.redis import get_redis_client

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis_client] = override_get_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    del app.dependency_overrides[get_db]
    del app.dependency_overrides[get_redis_client]


@pytest.mark.asyncio
async def test_calculate_pnl_with_mixed_sources(db_session: AsyncSession):
    prop = await _create_property(db_session)

    # Direct booking: no OTA commission
    await _create_booking(
        db_session, prop.id, date(2024, 6, 5), Decimal("1000.00"), SourceType.direct.value
    )
    # OTA booking (Airbnb): 15% OTA commission on 2000 = 300
    await _create_booking(
        db_session, prop.id, date(2024, 6, 10), Decimal("2000.00"), SourceType.gmail_airbnb.value
    )
    # ICal booking: also OTA
    await _create_booking(
        db_session, prop.id, date(2024, 6, 12), Decimal("1500.00"), SourceType.ical.value
    )

    svc = OwnerService(db_session, DEFAULT_ORG_ID)
    pnl = await svc.calculate_pnl(prop.id, date(2024, 6, 1))

    assert pnl["gross_amount"] == Decimal("4500.00")
    assert pnl["ota_commission"] == Decimal("525.00")  # 15% of 3500
    assert pnl["partner_commission"] == Decimal("0.00")
    assert pnl["net_distributable"] == Decimal("3975.00")
    assert pnl["booking_count"] == 3


@pytest.mark.asyncio
async def test_calculate_payout_split(db_session: AsyncSession):
    prop = await _create_property(db_session)
    await _create_booking(
        db_session, prop.id, date(2024, 7, 5), Decimal("1000.00"), SourceType.direct.value
    )

    svc = OwnerService(db_session, DEFAULT_ORG_ID)
    payout = await svc.calculate_payout(prop.id, date(2024, 7, 1))

    assert payout.owner_percentage == Decimal("70.00")
    assert payout.brekora_percentage == Decimal("30.00")
    assert payout.owner_share == Decimal("700.00")
    assert payout.brekora_share == Decimal("300.00")
    assert payout.net_distributable == Decimal("1000.00")
    assert payout.status == "pending"


@pytest.mark.asyncio
async def test_generate_statement(db_session: AsyncSession):
    prop = await _create_property(db_session)
    await _create_booking(
        db_session, prop.id, date(2024, 8, 5), Decimal("1000.00"), SourceType.direct.value
    )
    await _create_booking(
        db_session, prop.id, date(2024, 8, 10), Decimal("2000.00"), SourceType.gmail_mmt.value
    )

    svc = OwnerService(db_session, DEFAULT_ORG_ID)
    statement = await svc.generate_monthly_statement(prop.id, date(2024, 8, 1))

    assert statement["month"] == "2024-08"
    assert "summary" in statement
    assert "chart" in statement
    assert "bookings" in statement
    assert len(statement["bookings"]) == 2

    # Verify per-booking breakdown
    booking_breakdown = statement["bookings"]
    direct = next(b for b in booking_breakdown if b["source"] == SourceType.direct.value)
    assert direct["gross"] == Decimal("1000.00")
    assert direct["ota_commission"] == Decimal("0.00")
    assert direct["net"] == Decimal("1000.00")

    ota = next(b for b in booking_breakdown if b["source"] == SourceType.gmail_mmt.value)
    assert ota["gross"] == Decimal("2000.00")
    assert ota["ota_commission"] == Decimal("300.00")
    assert ota["net"] == Decimal("1700.00")


@pytest.mark.asyncio
async def test_ota_commission_configurable(db_session: AsyncSession):
    prop = await _create_property(db_session)
    await _create_booking(
        db_session, prop.id, date(2024, 9, 5), Decimal("2000.00"), SourceType.gmail_airbnb.value
    )

    # Set custom OTA commission rate to 20%
    repo = SystemConfigRepository(db_session, DEFAULT_ORG_ID)
    await repo.create({
        "key": "ota_commission_rate",
        "value": "20.0",
        "data_type": "number",
    })

    svc = OwnerService(db_session, DEFAULT_ORG_ID)
    pnl = await svc.calculate_pnl(prop.id, date(2024, 9, 1))

    assert pnl["ota_commission"] == Decimal("400.00")  # 20% of 2000
    assert pnl["net_distributable"] == Decimal("1600.00")


@pytest.mark.asyncio
async def test_partner_commission(db_session: AsyncSession):
    prop = await _create_property(db_session)
    await _create_booking(
        db_session,
        prop.id,
        date(2024, 10, 5),
        Decimal("1000.00"),
        SourceType.direct.value,
        partner_attribution_id="partner_123",
    )

    svc = OwnerService(db_session, DEFAULT_ORG_ID)
    pnl = await svc.calculate_pnl(prop.id, date(2024, 10, 1))

    # Default partner commission = 10%
    assert pnl["partner_commission"] == Decimal("100.00")
    assert pnl["net_distributable"] == Decimal("900.00")


@pytest.mark.asyncio
async def test_payout_idempotent(db_session: AsyncSession):
    prop = await _create_property(db_session)
    await _create_booking(
        db_session, prop.id, date(2024, 11, 5), Decimal("1000.00"), SourceType.direct.value
    )

    svc = OwnerService(db_session, DEFAULT_ORG_ID)
    payout1 = await svc.calculate_payout(prop.id, date(2024, 11, 1))

    # Add another booking and re-calculate
    await _create_booking(
        db_session, prop.id, date(2024, 11, 10), Decimal("500.00"), SourceType.direct.value
    )
    payout2 = await svc.calculate_payout(prop.id, date(2024, 11, 1))

    assert payout1.id == payout2.id
    assert payout2.gross_amount == Decimal("1500.00")
    assert payout2.owner_share == Decimal("1050.00")
    assert payout2.brekora_share == Decimal("450.00")


@pytest.mark.asyncio
async def test_api_pnl_endpoint(api_client: AsyncClient, db_session: AsyncSession):
    prop = await _create_property(db_session)
    user = await _create_user_with_role(db_session, "owner_pnl@example.com", "password", "Owner")
    token = await _login(api_client, "owner_pnl@example.com", "password")

    await _create_booking(
        db_session, prop.id, date(2024, 12, 5), Decimal("1000.00"), SourceType.direct.value
    )

    response = await api_client.get(
        f"/api/v1/owner/pnl?property_id={prop.id}&month=2024-12",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["gross_amount"] == 1000.0
    assert data["net_distributable"] == 1000.0


@pytest.mark.asyncio
async def test_api_payout_endpoint(api_client: AsyncClient, db_session: AsyncSession):
    prop = await _create_property(db_session)
    user = await _create_user_with_role(db_session, "owner_payout@example.com", "password", "Owner")
    token = await _login(api_client, "owner_payout@example.com", "password")

    await _create_booking(
        db_session, prop.id, date(2025, 1, 5), Decimal("2000.00"), SourceType.gmail_airbnb.value
    )

    response = await api_client.get(
        f"/api/v1/owner/payout?property_id={prop.id}&month=2025-01",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["gross_amount"] == 2000.0
    assert data["ota_commission"] == 300.0
    assert data["owner_share"] == 1190.0  # 70% of 1700
    assert data["brekora_share"] == 510.0  # 30% of 1700


@pytest.mark.asyncio
async def test_api_statement_endpoint(api_client: AsyncClient, db_session: AsyncSession):
    prop = await _create_property(db_session)
    user = await _create_user_with_role(db_session, "owner_stmt@example.com", "password", "Owner")
    token = await _login(api_client, "owner_stmt@example.com", "password")

    await _create_booking(
        db_session, prop.id, date(2025, 2, 5), Decimal("1000.00"), SourceType.direct.value
    )

    response = await api_client.get(
        f"/api/v1/owner/statement?property_id={prop.id}&month=2025-02",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "chart" in data
    assert "bookings" in data
    assert len(data["bookings"]) == 1


@pytest.mark.asyncio
async def test_api_admin_split_endpoint(api_client: AsyncClient, db_session: AsyncSession):
    admin = await _create_user_with_role(db_session, "admin_split@example.com", "password", "Admin")
    token = await _login(api_client, "admin_split@example.com", "password")

    response = await api_client.get(
        "/api/v1/gst/split",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["default_owner_split"] == "70.00"
    assert data["default_brekora_split"] == "30.00"

    # Update split
    patch_resp = await api_client.patch(
        "/api/v1/gst/split",
        json={"owner_percentage": "65.00", "brekora_percentage": "35.00"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patch_resp.status_code == 200
    patch_data = patch_resp.json()
    assert patch_data["default_owner_split"] == "65.00"
    assert patch_data["default_brekora_split"] == "35.00"

    # Verify persisted
    get_resp = await api_client.get(
        "/api/v1/gst/split",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["default_owner_split"] == "65.00"
