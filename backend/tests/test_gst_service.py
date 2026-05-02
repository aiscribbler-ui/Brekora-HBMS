import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import get_password_hash
from app.db.session import get_db
from app.main import app
from app.models.role import Role
from app.models.system_config import SystemConfig
from app.models.user import User
from app.repositories.system_config import SystemConfigRepository
from app.repositories.user import UserRepository
from app.services.gst_service import GSTService
from tests.conftest import FakeRedis

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


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


@pytest_asyncio.fixture
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
async def test_default_gst_calculation(db_session: AsyncSession):
    svc = GSTService(db_session)
    result = await svc.calculate(
        subtotal=Decimal("1000.00"),
        discount=Decimal("100.00"),
        org_id=DEFAULT_ORG_ID,
    )
    assert result["rate"] == Decimal("0.12")
    assert result["taxable_value"] == Decimal("900.00")
    assert result["gst_amount"] == Decimal("108.00")
    assert result["total"] == Decimal("1008.00")


@pytest.mark.asyncio
async def test_reverse_calculate_from_gross(db_session: AsyncSession):
    gross = Decimal("1120.00")
    rate = Decimal("0.12")
    result = GSTService.reverse_calculate(gross, rate)
    assert result["rate"] == Decimal("0.12")
    assert result["taxable_value"] == Decimal("1000.00")
    assert result["gst_amount"] == Decimal("120.00")
    assert result["total"] == Decimal("1120.00")


@pytest.mark.asyncio
async def test_property_specific_rate_override(db_session: AsyncSession):
    # Update existing default rate for the org (do not commit; rolled back by fixture)
    repo = SystemConfigRepository(db_session, DEFAULT_ORG_ID)
    config = await repo.get_by_key("gst_rate")
    if config is not None:
        await repo.update(config, {"value": "0.18"})
    else:
        await repo.create({"key": "gst_rate", "value": "0.18", "data_type": "number"})

    svc = GSTService(db_session)
    result = await svc.calculate(
        subtotal=Decimal("1000.00"),
        discount=Decimal("0.00"),
        org_id=DEFAULT_ORG_ID,
    )
    assert result["rate"] == Decimal("0.18")
    assert result["taxable_value"] == Decimal("1000.00")
    assert result["gst_amount"] == Decimal("180.00")
    assert result["total"] == Decimal("1180.00")


@pytest.mark.asyncio
async def test_rounding_to_two_decimals(db_session: AsyncSession):
    svc = GSTService(db_session)
    result = await svc.calculate(
        subtotal=Decimal("999.99"),
        discount=Decimal("0.00"),
        org_id=DEFAULT_ORG_ID,
    )
    # 999.99 * 0.12 = 119.9988 -> 120.00 after quantize
    assert result["gst_amount"] == Decimal("120.00")
    assert result["total"] == Decimal("1119.99")

    rev = GSTService.reverse_calculate(Decimal("1119.99"), Decimal("0.12"))
    assert rev["taxable_value"] == Decimal("999.99")
    assert rev["gst_amount"] == Decimal("120.00")


@pytest.mark.asyncio
async def test_api_endpoint_returns_rate(api_client: AsyncClient, db_session: AsyncSession):
    user = await _create_user_with_role(
        db_session, "gst_get@example.com", "password", "Guest"
    )
    token = await _login(api_client, "gst_get@example.com", "password")

    response = await api_client.get(
        "/api/v1/gst/rate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "gst_rate"
    assert data["value"] == "0.12"
    assert data["data_type"] == "number"


@pytest.mark.asyncio
async def test_api_patch_rate_admin(api_client: AsyncClient, db_session: AsyncSession):
    admin = await _create_user_with_role(
        db_session, "gst_admin@example.com", "password", "Admin"
    )
    token = await _login(api_client, "gst_admin@example.com", "password")

    response = await api_client.patch(
        "/api/v1/gst/rate",
        json={"value": "0.05"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["value"] == "0.05"

    # Verify it persisted
    get_resp = await api_client.get(
        "/api/v1/gst/rate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["value"] == "0.05"
