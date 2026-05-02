import uuid
from io import BytesIO

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.property import Property
from app.models.room_type import RoomType
from app.repositories.property import PropertyRepository
from app.repositories.room_type import RoomTypeRepository

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.mark.asyncio(loop_scope="session")
async def test_property_repository_crud(db_session: AsyncSession):
    repo = PropertyRepository(db_session, DEFAULT_ORG_ID)

    # Create
    prop = await repo.create({"name": "Test Hotel", "address": "123 Main St"})
    assert prop.id is not None
    assert prop.name == "Test Hotel"
    assert prop.org_id == DEFAULT_ORG_ID

    # Get
    fetched = await repo.get(prop.id)
    assert fetched is not None
    assert fetched.name == "Test Hotel"

    # Update
    updated = await repo.update(fetched, {"name": "Updated Hotel"})
    assert updated.name == "Updated Hotel"

    # List
    items = await repo.get_multi()
    assert any(i.id == prop.id for i in items)

    # Archive (soft delete)
    archived = await repo.update(updated, {"is_archived": True, "is_active": False})
    assert archived.is_archived is True
    assert archived.is_active is False


@pytest.mark.asyncio(loop_scope="session")
async def test_room_type_repository_crud(db_session: AsyncSession):
    prop_repo = PropertyRepository(db_session, DEFAULT_ORG_ID)
    prop = await prop_repo.create({"name": "Test Hotel"})

    repo = RoomTypeRepository(db_session, DEFAULT_ORG_ID)

    # Create
    rt = await repo.create(
        {
            "property_id": prop.id,
            "name": "Deluxe",
            "count": 5,
            "base_capacity": 2,
            "max_capacity": 3,
            "default_rate": 100.00,
        }
    )
    assert rt.id is not None
    assert rt.name == "Deluxe"
    assert rt.property_id == prop.id
    assert rt.org_id == DEFAULT_ORG_ID

    # Get
    fetched = await repo.get(rt.id)
    assert fetched is not None
    assert fetched.name == "Deluxe"

    # List by property
    items = await repo.get_multi_by_property(prop.id)
    assert len(items) == 1
    assert items[0].id == rt.id

    # Update
    updated = await repo.update(fetched, {"name": "Super Deluxe"})
    assert updated.name == "Super Deluxe"

    # Delete
    await repo.delete(updated)
    after_delete = await repo.get(rt.id)
    assert after_delete is None


@pytest.mark.asyncio(loop_scope="session")
async def test_property_api_crud(client: AsyncClient):
    # Create
    response = await client.post(
        "/api/v1/properties/",
        json={"name": "API Hotel", "address": "456 Oak Ave", "gstin": "22AAAAA0000A1Z5"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "API Hotel"
    assert data["address"] == "456 Oak Ave"
    assert data["gstin"] == "22AAAAA0000A1Z5"
    assert data["org_id"] == str(DEFAULT_ORG_ID)
    prop_id = data["id"]

    # List
    response = await client.get("/api/v1/properties/")
    assert response.status_code == 200
    items = response.json()
    assert any(i["id"] == prop_id for i in items)

    # Get
    response = await client.get(f"/api/v1/properties/{prop_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "API Hotel"

    # Update
    response = await client.patch(
        f"/api/v1/properties/{prop_id}",
        json={"name": "Updated API Hotel"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated API Hotel"

    # Soft delete (archive)
    response = await client.delete(f"/api/v1/properties/{prop_id}")
    assert response.status_code == 204

    # Verify archived property is not found
    response = await client.get(f"/api/v1/properties/{prop_id}")
    assert response.status_code == 404


@pytest.mark.asyncio(loop_scope="session")
async def test_room_type_api_nested_crud(client: AsyncClient):
    # Create property
    response = await client.post(
        "/api/v1/properties/",
        json={"name": "Nested Hotel"},
    )
    assert response.status_code == 201
    prop_id = response.json()["id"]

    # Create room type
    response = await client.post(
        f"/api/v1/properties/{prop_id}/room-types",
        json={
            "name": "Standard",
            "count": 10,
            "base_capacity": 2,
            "max_capacity": 4,
            "default_rate": 150.00,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Standard"
    assert data["property_id"] == prop_id
    rt_id = data["id"]

    # List room types under property
    response = await client.get(f"/api/v1/properties/{prop_id}/room-types")
    assert response.status_code == 200
    items = response.json()
    assert any(i["id"] == rt_id for i in items)

    # Get room type via standalone endpoint
    response = await client.get(f"/api/v1/room-types/{rt_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Standard"

    # Update room type
    response = await client.patch(
        f"/api/v1/room-types/{rt_id}",
        json={"name": "Premium Standard", "count": 12},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Premium Standard"
    assert response.json()["count"] == 12

    # Delete room type
    response = await client.delete(f"/api/v1/room-types/{rt_id}")
    assert response.status_code == 204

    # Verify deletion
    response = await client.get(f"/api/v1/room-types/{rt_id}")
    assert response.status_code == 404


@pytest.mark.asyncio(loop_scope="session")
async def test_property_photo_upload(client: AsyncClient):
    # Create property
    response = await client.post(
        "/api/v1/properties/",
        json={"name": "Photo Hotel"},
    )
    assert response.status_code == 201
    prop_id = response.json()["id"]

    # Upload photos
    files = [
        ("files", ("room1.jpg", b"fake image data 1", "image/jpeg")),
        ("files", ("room2.jpg", b"fake image data 2", "image/jpeg")),
    ]
    response = await client.post(
        f"/api/v1/properties/{prop_id}/photos",
        files=files,
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["photos"]) == 2
    assert data["photos"][0]["filename"] == "room1.jpg"
    assert data["photos"][1]["filename"] == "room2.jpg"
    assert "/uploads/" in data["photos"][0]["path"]


@pytest.mark.asyncio(loop_scope="session")
async def test_property_not_found(client: AsyncClient):
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/api/v1/properties/{fake_id}")
    assert response.status_code == 404

    response = await client.patch(f"/api/v1/properties/{fake_id}", json={"name": "X"})
    assert response.status_code == 404

    response = await client.delete(f"/api/v1/properties/{fake_id}")
    assert response.status_code == 404

    response = await client.post(f"/api/v1/properties/{fake_id}/room-types", json={"name": "X"})
    assert response.status_code == 404

    files = [("files", ("fake.jpg", b"data", "image/jpeg"))]
    response = await client.post(f"/api/v1/properties/{fake_id}/photos", files=files)
    assert response.status_code == 404
