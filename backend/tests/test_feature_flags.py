import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis_client
from app.db.session import get_db
from app.main import app
from app.models.feature_flag import FeatureFlag
from app.repositories.feature_flag import FeatureFlagRepository
from tests.conftest import FakeRedis

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest_asyncio.fixture(loop_scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    fake_redis = FakeRedis()

    async def override_get_redis() -> FakeRedis:
        return fake_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis_client] = override_get_redis
    app.state.rate_limit_config = {
        "search": {"max_requests": 10000, "window_seconds": 60, "identifier_type": "ip"},
        "hold": {"max_requests": 10000, "window_seconds": 600, "identifier_type": "session"},
        "promo": {"max_requests": 10000, "window_seconds": 60, "identifier_type": "ip"},
        "booking": {"max_requests": 10000, "window_seconds": 300, "identifier_type": "session"},
        "login": {"max_requests": 10000, "window_seconds": 900, "identifier_type": "ip"},
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    del app.dependency_overrides[get_db]
    del app.dependency_overrides[get_redis_client]
    if hasattr(app.state, "rate_limit_config"):
        delattr(app.state, "rate_limit_config")


@pytest.mark.asyncio
async def test_feature_flag_repository_crud(db_session: AsyncSession):
    repo = FeatureFlagRepository(db_session, DEFAULT_ORG_ID)

    # Create
    flag = await repo.create(
        {
            "key": "dark_mode",
            "name": "Dark Mode",
            "description": "Enable dark mode UI",
            "enabled": True,
            "value": "true",
            "scope": "org",
        }
    )
    assert flag.id is not None
    assert flag.key == "dark_mode"
    assert flag.enabled is True
    assert flag.org_id == DEFAULT_ORG_ID

    # Get
    fetched = await repo.get(flag.id)
    assert fetched is not None
    assert fetched.key == "dark_mode"

    # Get by key
    by_key = await repo.get_by_key("dark_mode")
    assert by_key is not None
    assert by_key.id == flag.id

    # Update
    updated = await repo.update(fetched, {"enabled": False})
    assert updated.enabled is False

    # List
    items = await repo.get_multi()
    assert any(i.id == flag.id for i in items)

    # Delete
    await repo.delete(updated)
    after_delete = await repo.get(flag.id)
    assert after_delete is None


@pytest.mark.asyncio
async def test_feature_flag_api_crud(client: AsyncClient):
    # Create flag
    response = await client.post(
        "/api/v1/feature-flags/",
        json={
            "key": "beta_feature",
            "name": "Beta Feature",
            "description": "New beta feature",
            "enabled": False,
            "value": "false",
            "scope": "org",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["key"] == "beta_feature"
    assert data["enabled"] is False
    flag_id = data["id"]

    # List
    response = await client.get("/api/v1/feature-flags/")
    assert response.status_code == 200
    items = response.json()
    assert any(i["id"] == flag_id for i in items)

    # Get
    response = await client.get(f"/api/v1/feature-flags/{flag_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Beta Feature"

    # Update
    response = await client.patch(
        f"/api/v1/feature-flags/{flag_id}",
        json={"enabled": True, "value": "true"},
    )
    assert response.status_code == 200
    assert response.json()["enabled"] is True
    assert response.json()["value"] == "true"

    # Check endpoint
    response = await client.get("/api/v1/feature-flags/check/beta_feature")
    assert response.status_code == 200
    check_data = response.json()
    assert check_data["enabled"] is True
    assert check_data["value"] == "true"

    # Delete
    response = await client.delete(f"/api/v1/feature-flags/{flag_id}")
    assert response.status_code == 204

    # Verify deletion
    response = await client.get(f"/api/v1/feature-flags/{flag_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_feature_flag_check_not_found(client: AsyncClient):
    response = await client.get("/api/v1/feature-flags/check/nonexistent_key")
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is False
    assert data["value"] is None


@pytest.mark.asyncio
async def test_feature_flag_not_found(client: AsyncClient):
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/api/v1/feature-flags/{fake_id}")
    assert response.status_code == 404

    response = await client.patch(f"/api/v1/feature-flags/{fake_id}", json={"enabled": True})
    assert response.status_code == 404

    response = await client.delete(f"/api/v1/feature-flags/{fake_id}")
    assert response.status_code == 404
