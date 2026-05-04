import uuid
from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.add_on import AddOn, AddOnType
from app.models.add_on_capacity import AddOnCapacity
from app.repositories.add_on import AddOnCapacityRepository, AddOnRepository
from app.repositories.property import PropertyRepository

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.mark.asyncio
async def test_add_on_repository_crud(db_session: AsyncSession):
    prop_repo = PropertyRepository(db_session, DEFAULT_ORG_ID)
    prop = await prop_repo.create({"name": "AddOn Test Hotel"})

    repo = AddOnRepository(db_session, DEFAULT_ORG_ID)

    # Create
    addon = await repo.create(
        {
            "property_id": prop.id,
            "name": "Yoga Class",
            "description": "Morning yoga session",
            "type": "slot",
            "default_capacity": 10,
            "unit_price": Decimal("25.00"),
        }
    )
    assert addon.id is not None
    assert addon.name == "Yoga Class"
    assert addon.property_id == prop.id
    assert addon.org_id == DEFAULT_ORG_ID
    assert addon.type == AddOnType.slot

    # Get
    fetched = await repo.get(addon.id)
    assert fetched is not None
    assert fetched.name == "Yoga Class"

    # Update
    updated = await repo.update(fetched, {"name": "Yoga Deluxe", "default_capacity": 12})
    assert updated.name == "Yoga Deluxe"
    assert updated.default_capacity == 12

    # List
    items = await repo.get_multi()
    assert any(i.id == addon.id for i in items)

    # List by property
    prop_items = await repo.get_multi_by_property(prop.id)
    assert len(prop_items) == 1
    assert prop_items[0].id == addon.id

    # Archive
    archived = await repo.update(updated, {"is_archived": True, "is_active": False})
    assert archived.is_archived is True
    assert archived.is_active is False


@pytest.mark.asyncio
async def test_add_on_capacity_repository_crud(db_session: AsyncSession):
    prop_repo = PropertyRepository(db_session, DEFAULT_ORG_ID)
    prop = await prop_repo.create({"name": "Capacity Test Hotel"})

    addon_repo = AddOnRepository(db_session, DEFAULT_ORG_ID)
    addon = await addon_repo.create(
        {
            "property_id": prop.id,
            "name": "Dinner",
            "type": "day",
            "default_capacity": 20,
            "unit_price": Decimal("15.00"),
        }
    )

    cap_repo = AddOnCapacityRepository(db_session)

    # Create
    cap = await cap_repo.create(
        {
            "add_on_id": addon.id,
            "date": date(2026, 5, 1),
            "slot_time": None,
            "available_capacity": 20,
            "total_capacity": 20,
        }
    )
    assert cap.id is not None
    assert cap.add_on_id == addon.id
    assert cap.date == date(2026, 5, 1)
    assert cap.slot_time is None

    # Get
    fetched = await cap_repo.get(cap.id)
    assert fetched is not None
    assert fetched.available_capacity == 20

    # List by add-on
    items = await cap_repo.get_multi_by_add_on(addon.id)
    assert len(items) == 1
    assert items[0].id == cap.id

    # Update
    updated = await cap_repo.update(fetched, {"available_capacity": 15})
    assert updated.available_capacity == 15

    # Delete
    await cap_repo.delete(updated)
    after_delete = await cap_repo.get(cap.id)
    assert after_delete is None


@pytest.mark.asyncio
async def test_add_on_api_crud(client: AsyncClient):
    # Create property
    response = await client.post("/api/v1/properties/", json={"name": "API AddOn Hotel"})
    assert response.status_code == 201
    prop_id = response.json()["id"]

    # Create add-on
    response = await client.post(
        "/api/v1/add-ons/",
        json={
            "name": "Spa Treatment",
            "description": "Relaxing massage",
            "type": "day",
            "default_capacity": 5,
            "unit_price": "50.00",
            "property_id": prop_id,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Spa Treatment"
    assert data["property_id"] == prop_id
    assert data["type"] == "day"
    addon_id = data["id"]

    # List add-ons
    response = await client.get("/api/v1/add-ons/")
    assert response.status_code == 200
    items = response.json()
    assert any(i["id"] == addon_id for i in items)

    # Get add-on
    response = await client.get(f"/api/v1/add-ons/{addon_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Spa Treatment"

    # Update add-on
    response = await client.patch(
        f"/api/v1/add-ons/{addon_id}",
        json={"name": "Spa Treatment Deluxe", "unit_price": "75.00"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Spa Treatment Deluxe"
    assert response.json()["unit_price"] == "75.00"

    # Soft delete
    response = await client.delete(f"/api/v1/add-ons/{addon_id}")
    assert response.status_code == 204

    # Verify archived
    response = await client.get(f"/api/v1/add-ons/{addon_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_add_on_capacity_api_crud(client: AsyncClient):
    # Create property and add-on
    response = await client.post("/api/v1/properties/", json={"name": "Capacity API Hotel"})
    assert response.status_code == 201
    prop_id = response.json()["id"]

    response = await client.post(
        "/api/v1/add-ons/",
        json={
            "name": "Dinner Buffet",
            "type": "day",
            "default_capacity": 30,
            "unit_price": "20.00",
            "property_id": prop_id,
        },
    )
    assert response.status_code == 201
    addon_id = response.json()["id"]

    # Create capacity
    response = await client.post(
        f"/api/v1/add-ons/{addon_id}/capacity",
        json={
            "date": "2026-05-10",
            "available_capacity": 30,
            "total_capacity": 30,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["date"] == "2026-05-10"
    assert data["available_capacity"] == 30
    cap_id = data["id"]

    # List capacities
    response = await client.get(f"/api/v1/add-ons/{addon_id}/capacity")
    assert response.status_code == 200
    items = response.json()
    assert any(i["id"] == cap_id for i in items)

    # Update capacity
    response = await client.patch(
        f"/api/v1/add-ons/capacity/{cap_id}",
        json={"available_capacity": 25},
    )
    assert response.status_code == 200
    assert response.json()["available_capacity"] == 25

    # Delete capacity
    response = await client.delete(f"/api/v1/add-ons/capacity/{cap_id}")
    assert response.status_code == 204

    # Verify deletion
    response = await client.get(f"/api/v1/add-ons/capacity/{cap_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_capacity_day_based(client: AsyncClient):
    # Create property and day-based add-on
    response = await client.post("/api/v1/properties/", json={"name": "Gen Day Hotel"})
    assert response.status_code == 201
    prop_id = response.json()["id"]

    response = await client.post(
        "/api/v1/add-ons/",
        json={
            "name": "Breakfast",
            "type": "day",
            "default_capacity": 40,
            "unit_price": "10.00",
            "property_id": prop_id,
        },
    )
    assert response.status_code == 201
    addon_id = response.json()["id"]

    # Generate capacity for 3 days
    response = await client.post(
        f"/api/v1/add-ons/{addon_id}/generate-capacity",
        json={
            "start_date": "2026-06-01",
            "end_date": "2026-06-03",
        },
    )
    assert response.status_code == 201
    items = response.json()
    assert len(items) == 3
    dates = {item["date"] for item in items}
    assert dates == {"2026-06-01", "2026-06-02", "2026-06-03"}
    for item in items:
        assert item["slot_time"] is None
        assert item["available_capacity"] == 40
        assert item["total_capacity"] == 40

    # Re-generate should skip existing
    response = await client.post(
        f"/api/v1/add-ons/{addon_id}/generate-capacity",
        json={
            "start_date": "2026-06-01",
            "end_date": "2026-06-03",
        },
    )
    assert response.status_code == 201
    items = response.json()
    assert len(items) == 0


@pytest.mark.asyncio
async def test_generate_capacity_slot_based(client: AsyncClient):
    # Create property and slot-based add-on
    response = await client.post(
        "/api/v1/properties/", json={"name": "Gen Slot Hotel"}
    )
    assert response.status_code == 201
    prop_id = response.json()["id"]

    response = await client.post(
        "/api/v1/add-ons/",
        json={
            "name": "Yoga",
            "type": "slot",
            "default_capacity": 8,
            "unit_price": "15.00",
            "property_id": prop_id,
        },
    )
    assert response.status_code == 201
    addon_id = response.json()["id"]

    # Generate capacity for 2 days with 2 slots
    response = await client.post(
        f"/api/v1/add-ons/{addon_id}/generate-capacity",
        json={
            "start_date": "2026-06-10",
            "end_date": "2026-06-11",
            "slot_times": ["09:00:00", "17:00:00"],
        },
    )
    assert response.status_code == 201
    items = response.json()
    assert len(items) == 4
    for item in items:
        assert item["available_capacity"] == 8
        assert item["total_capacity"] == 8
        assert item["slot_time"] in ("09:00:00", "17:00:00")


@pytest.mark.asyncio
async def test_generate_capacity_package_instance_rejected(client: AsyncClient):
    response = await client.post(
        "/api/v1/properties/", json={"name": "Gen Pkg Hotel"}
    )
    assert response.status_code == 201
    prop_id = response.json()["id"]

    response = await client.post(
        "/api/v1/add-ons/",
        json={
            "name": "Premium Decor",
            "type": "package_instance",
            "default_capacity": 0,
            "unit_price": "100.00",
            "property_id": prop_id,
        },
    )
    assert response.status_code == 201
    addon_id = response.json()["id"]

    response = await client.post(
        f"/api/v1/add-ons/{addon_id}/generate-capacity",
        json={
            "start_date": "2026-06-01",
            "end_date": "2026-06-01",
        },
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_generate_capacity_slot_times_required(client: AsyncClient):
    response = await client.post(
        "/api/v1/properties/", json={"name": "Gen SlotReq Hotel"}
    )
    assert response.status_code == 201
    prop_id = response.json()["id"]

    response = await client.post(
        "/api/v1/add-ons/",
        json={
            "name": "Pilates",
            "type": "slot",
            "default_capacity": 6,
            "unit_price": "20.00",
            "property_id": prop_id,
        },
    )
    assert response.status_code == 201
    addon_id = response.json()["id"]

    response = await client.post(
        f"/api/v1/add-ons/{addon_id}/generate-capacity",
        json={
            "start_date": "2026-06-01",
            "end_date": "2026-06-01",
        },
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_add_on_not_found(client: AsyncClient):
    fake_id = str(uuid.uuid4())

    response = await client.get(f"/api/v1/add-ons/{fake_id}")
    assert response.status_code == 404

    response = await client.patch(f"/api/v1/add-ons/{fake_id}", json={"name": "X"})
    assert response.status_code == 404

    response = await client.delete(f"/api/v1/add-ons/{fake_id}")
    assert response.status_code == 404

    response = await client.get(f"/api/v1/add-ons/{fake_id}/capacity")
    assert response.status_code == 404

    response = await client.post(
        f"/api/v1/add-ons/{fake_id}/capacity",
        json={"date": "2026-05-01", "available_capacity": 10, "total_capacity": 10},
    )
    assert response.status_code == 404

    response = await client.post(
        f"/api/v1/add-ons/{fake_id}/generate-capacity",
        json={"start_date": "2026-05-01", "end_date": "2026-05-01"},
    )
    assert response.status_code == 404
