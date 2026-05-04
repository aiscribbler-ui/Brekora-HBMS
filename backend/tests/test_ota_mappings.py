import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.property import Property
from app.models.room_type import RoomType
from app.repositories.ota_mapping import OTAMappingRepository
from app.repositories.property import PropertyRepository
from app.repositories.room_type import RoomTypeRepository

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.mark.asyncio
async def test_ota_mapping_repository_crud(db_session: AsyncSession):
    # Create property and room type first
    prop_repo = PropertyRepository(db_session, DEFAULT_ORG_ID)
    prop = await prop_repo.create({"name": "OTA Test Hotel"})

    rt_repo = RoomTypeRepository(db_session, DEFAULT_ORG_ID)
    rt = await rt_repo.create(
        {
            "property_id": prop.id,
            "name": "Deluxe",
            "count": 5,
            "base_capacity": 2,
            "max_capacity": 3,
            "default_rate": 100.00,
        }
    )

    repo = OTAMappingRepository(db_session, DEFAULT_ORG_ID)

    # Create
    mapping = await repo.create(
        {
            "ota_source": "airbnb",
            "listing_id": "12345",
            "room_type_id": rt.id,
            "property_id": prop.id,
        }
    )
    assert mapping.id is not None
    assert mapping.ota_source == "airbnb"
    assert mapping.listing_id == "12345"
    assert mapping.room_type_id == rt.id
    assert mapping.property_id == prop.id
    assert mapping.org_id == DEFAULT_ORG_ID
    assert mapping.is_active is True

    # Get
    fetched = await repo.get(mapping.id)
    assert fetched is not None
    assert fetched.ota_source == "airbnb"
    assert fetched.listing_id == "12345"

    # Update
    updated = await repo.update(fetched, {"listing_id": "67890"})
    assert updated.listing_id == "67890"

    # List
    items = await repo.get_multi()
    assert any(i.id == mapping.id for i in items)

    # Delete
    await repo.delete(updated)
    after_delete = await repo.get(mapping.id)
    assert after_delete is None


@pytest.mark.asyncio
async def test_ota_mapping_api_crud(client: AsyncClient):
    # Create property
    response = await client.post(
        "/api/v1/properties/",
        json={"name": "API OTA Hotel"},
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
    rt_id = response.json()["id"]

    # Create mapping
    response = await client.post(
        "/api/v1/ota/mappings/",
        json={
            "ota_source": "airbnb",
            "listing_id": "airbnb_123",
            "room_type_id": str(rt_id),
            "property_id": str(prop_id),
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["ota_source"] == "airbnb"
    assert data["listing_id"] == "airbnb_123"
    assert data["room_type_id"] == str(rt_id)
    assert data["property_id"] == str(prop_id)
    mapping_id = data["id"]

    # List
    response = await client.get("/api/v1/ota/mappings/")
    assert response.status_code == 200
    items = response.json()
    assert any(i["id"] == mapping_id for i in items)

    # Get
    response = await client.get(f"/api/v1/ota/mappings/{mapping_id}")
    assert response.status_code == 200
    assert response.json()["listing_id"] == "airbnb_123"

    # Update
    response = await client.patch(
        f"/api/v1/ota/mappings/{mapping_id}",
        json={"listing_id": "airbnb_456"},
    )
    assert response.status_code == 200
    assert response.json()["listing_id"] == "airbnb_456"

    # Delete
    response = await client.delete(f"/api/v1/ota/mappings/{mapping_id}")
    assert response.status_code == 204

    # Verify soft delete
    response = await client.get(f"/api/v1/ota/mappings/{mapping_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_ota_mapping_unique_constraint(client: AsyncClient):
    # Create property
    response = await client.post(
        "/api/v1/properties/",
        json={"name": "Unique Constraint Hotel"},
    )
    assert response.status_code == 201
    prop_id = response.json()["id"]

    # Create room type
    response = await client.post(
        f"/api/v1/properties/{prop_id}/room-types",
        json={
            "name": "Suite",
            "count": 2,
            "base_capacity": 2,
            "max_capacity": 2,
            "default_rate": 200.00,
        },
    )
    assert response.status_code == 201
    rt_id = response.json()["id"]

    # First mapping
    response = await client.post(
        "/api/v1/ota/mappings/",
        json={
            "ota_source": "mmt",
            "listing_id": "mmt_123",
            "room_type_id": str(rt_id),
            "property_id": str(prop_id),
        },
    )
    assert response.status_code == 201

    # Duplicate should fail with 409 conflict
    response = await client.post(
        "/api/v1/ota/mappings/",
        json={
            "ota_source": "mmt",
            "listing_id": "mmt_123",
            "room_type_id": str(rt_id),
            "property_id": str(prop_id),
        },
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_ota_mapping_invalid_property_or_room_type(client: AsyncClient):
    fake_id = str(uuid.uuid4())

    response = await client.post(
        "/api/v1/ota/mappings/",
        json={
            "ota_source": "goibibo",
            "listing_id": "goibibo_123",
            "room_type_id": fake_id,
            "property_id": fake_id,
        },
    )
    assert response.status_code == 404
