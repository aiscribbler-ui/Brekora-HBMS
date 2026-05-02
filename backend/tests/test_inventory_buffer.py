import uuid
from datetime import date
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis_client
from app.db.session import get_db
from app.main import app
from app.models.inventory_buffer import InventoryBuffer
from app.models.property import Property
from app.repositories.inventory_buffer import InventoryBufferRepository
from app.repositories.property import PropertyRepository
from tests.conftest import FakeRedis

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest_asyncio.fixture
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
async def test_inventory_buffer_repository_crud(db_session: AsyncSession):
    prop_repo = PropertyRepository(db_session, DEFAULT_ORG_ID)
    prop = await prop_repo.create({"name": "Buffer Hotel"})

    repo = InventoryBufferRepository(db_session, DEFAULT_ORG_ID)

    # Create
    buf = await repo.create(
        {
            "property_id": prop.id,
            "room_type_id": None,
            "date": date(2026, 5, 1),
            "buffer_count": 3,
            "reason": "Maintenance",
        }
    )
    assert buf.id is not None
    assert buf.property_id == prop.id
    assert buf.buffer_count == 3
    assert buf.org_id == DEFAULT_ORG_ID

    # Get
    fetched = await repo.get(buf.id)
    assert fetched is not None
    assert fetched.buffer_count == 3

    # Update
    updated = await repo.update(fetched, {"buffer_count": 5})
    assert updated.buffer_count == 5

    # List
    items = await repo.get_multi()
    assert any(i.id == buf.id for i in items)

    # Delete
    await repo.delete(updated)
    after_delete = await repo.get(buf.id)
    assert after_delete is None


@pytest.mark.asyncio
async def test_inventory_buffer_api_crud(client: AsyncClient):
    # Create property
    response = await client.post(
        "/api/v1/properties/",
        json={"name": "API Buffer Hotel"},
    )
    assert response.status_code == 201
    prop_id = response.json()["id"]

    # Create buffer
    response = await client.post(
        "/api/v1/inventory-buffers/",
        json={
            "property_id": prop_id,
            "date": "2026-05-01",
            "buffer_count": 2,
            "reason": "Buffer reason",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["property_id"] == prop_id
    assert data["buffer_count"] == 2
    assert data["reason"] == "Buffer reason"
    buf_id = data["id"]

    # List
    response = await client.get("/api/v1/inventory-buffers/")
    assert response.status_code == 200
    items = response.json()
    assert any(i["id"] == buf_id for i in items)

    # Get
    response = await client.get(f"/api/v1/inventory-buffers/{buf_id}")
    assert response.status_code == 200
    assert response.json()["buffer_count"] == 2

    # Update
    response = await client.patch(
        f"/api/v1/inventory-buffers/{buf_id}",
        json={"buffer_count": 4},
    )
    assert response.status_code == 200
    assert response.json()["buffer_count"] == 4

    # Delete
    response = await client.delete(f"/api/v1/inventory-buffers/{buf_id}")
    assert response.status_code == 204

    # Verify deletion
    response = await client.get(f"/api/v1/inventory-buffers/{buf_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_inventory_buffer_not_found(client: AsyncClient):
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/api/v1/inventory-buffers/{fake_id}")
    assert response.status_code == 404

    response = await client.patch(f"/api/v1/inventory-buffers/{fake_id}", json={"buffer_count": 1})
    assert response.status_code == 404

    response = await client.delete(f"/api/v1/inventory-buffers/{fake_id}")
    assert response.status_code == 404
