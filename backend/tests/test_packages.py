import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.package import Package, PackageAddOn, PackageComposition
from app.repositories.package import (
    PackageAddOnRepository,
    PackageCompositionRepository,
    PackageRepository,
)
from app.repositories.add_on import AddOnRepository
from app.repositories.property import PropertyRepository
from app.repositories.room_type import RoomTypeRepository

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.mark.asyncio
async def test_package_repository_crud(db_session: AsyncSession):
    prop_repo = PropertyRepository(db_session, DEFAULT_ORG_ID)
    prop = await prop_repo.create({"name": "Package Test Hotel"})

    repo = PackageRepository(db_session, DEFAULT_ORG_ID)

    # Create
    pkg = await repo.create(
        {
            "property_id": prop.id,
            "name": "Weekend Special",
            "description": "A nice package",
            "status": "active",
            "base_price": 299.99,
            "max_occupancy": 4,
        }
    )
    assert pkg.id is not None
    assert pkg.name == "Weekend Special"
    assert pkg.property_id == prop.id
    assert pkg.org_id == DEFAULT_ORG_ID

    # Get
    fetched = await repo.get(pkg.id)
    assert fetched is not None
    assert fetched.name == "Weekend Special"

    # Update
    updated = await repo.update(fetched, {"name": "Weekend Deluxe"})
    assert updated.name == "Weekend Deluxe"

    # List
    items = await repo.get_multi()
    assert any(i.id == pkg.id for i in items)

    # List by property
    prop_items = await repo.get_multi_by_property(prop.id)
    assert len(prop_items) == 1
    assert prop_items[0].id == pkg.id

    # Archive
    archived = await repo.update(updated, {"is_archived": True, "is_active": False})
    assert archived.is_archived is True
    assert archived.is_active is False


@pytest.mark.asyncio
async def test_package_composition_repository_crud(db_session: AsyncSession):
    prop_repo = PropertyRepository(db_session, DEFAULT_ORG_ID)
    prop = await prop_repo.create({"name": "Comp Test Hotel"})

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

    pkg_repo = PackageRepository(db_session, DEFAULT_ORG_ID)
    pkg = await pkg_repo.create(
        {"property_id": prop.id, "name": "Comp Package", "base_price": 500.00}
    )

    repo = PackageCompositionRepository(db_session, DEFAULT_ORG_ID)

    # Create
    comp = await repo.create(
        {
            "package_id": pkg.id,
            "room_type_id": rt.id,
            "quantity": 2,
            "nights": 3,
        }
    )
    assert comp.id is not None
    assert comp.quantity == 2
    assert comp.nights == 3
    assert comp.org_id == DEFAULT_ORG_ID

    # Get
    fetched = await repo.get(comp.id)
    assert fetched is not None
    assert fetched.room_type_id == rt.id

    # List by package
    items = await repo.get_multi_by_package(pkg.id)
    assert len(items) == 1
    assert items[0].id == comp.id

    # Update
    updated = await repo.update(fetched, {"quantity": 5})
    assert updated.quantity == 5

    # Delete
    await repo.delete(updated)
    after_delete = await repo.get(comp.id)
    assert after_delete is None


@pytest.mark.asyncio
async def test_package_add_on_repository_crud(db_session: AsyncSession):
    prop_repo = PropertyRepository(db_session, DEFAULT_ORG_ID)
    prop = await prop_repo.create({"name": "AddOn Test Hotel"})

    pkg_repo = PackageRepository(db_session, DEFAULT_ORG_ID)
    pkg = await pkg_repo.create(
        {"property_id": prop.id, "name": "AddOn Package", "base_price": 300.00}
    )

    add_on_repo = AddOnRepository(db_session, DEFAULT_ORG_ID)
    add_on = await add_on_repo.create(
        {"property_id": prop.id, "name": "Spa", "type": "day", "unit_price": 50.00}
    )

    repo = PackageAddOnRepository(db_session, DEFAULT_ORG_ID)

    # Create
    pao = await repo.create(
        {
            "package_id": pkg.id,
            "add_on_id": add_on.id,
            "quantity": 2,
            "is_included": True,
        }
    )
    assert pao.id is not None
    assert pao.quantity == 2
    assert pao.is_included is True
    assert pao.org_id == DEFAULT_ORG_ID

    # Get
    fetched = await repo.get(pao.id)
    assert fetched is not None
    assert fetched.add_on_id == add_on.id

    # List by package
    items = await repo.get_multi_by_package(pkg.id)
    assert len(items) == 1
    assert items[0].id == pao.id

    # Update
    updated = await repo.update(fetched, {"quantity": 4, "is_included": False})
    assert updated.quantity == 4
    assert updated.is_included is False

    # Delete
    await repo.delete(updated)
    after_delete = await repo.get(pao.id)
    assert after_delete is None


@pytest.mark.asyncio
async def test_package_api_crud(client: AsyncClient):
    # Create property
    response = await client.post(
        "/api/v1/properties/",
        json={"name": "API Package Hotel"},
    )
    assert response.status_code == 201
    prop_id = response.json()["id"]

    # Create package via property nested endpoint
    response = await client.post(
        f"/api/v1/properties/{prop_id}/packages",
        json={
            "name": "Summer Deal",
            "description": "Best summer offer",
            "status": "active",
            "base_price": "199.99",
            "max_occupancy": 2,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Summer Deal"
    assert data["property_id"] == prop_id
    assert data["status"] == "active"
    pkg_id = data["id"]

    # List packages for property
    response = await client.get(f"/api/v1/properties/{prop_id}/packages")
    assert response.status_code == 200
    items = response.json()
    assert any(i["id"] == pkg_id for i in items)

    # List all packages
    response = await client.get("/api/v1/packages/")
    assert response.status_code == 200
    items = response.json()
    assert any(i["id"] == pkg_id for i in items)

    # Get package
    response = await client.get(f"/api/v1/packages/{pkg_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Summer Deal"

    # Update package
    response = await client.patch(
        f"/api/v1/packages/{pkg_id}",
        json={"name": "Summer Deal Updated", "base_price": "249.99"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Summer Deal Updated"
    assert response.json()["base_price"] == "249.99"

    # Soft delete
    response = await client.delete(f"/api/v1/packages/{pkg_id}")
    assert response.status_code == 204

    # Verify archived
    response = await client.get(f"/api/v1/packages/{pkg_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_package_composition_api_crud(client: AsyncClient):
    # Create property and room type
    response = await client.post(
        "/api/v1/properties/",
        json={"name": "Comp API Hotel"},
    )
    assert response.status_code == 201
    prop_id = response.json()["id"]

    response = await client.post(
        f"/api/v1/properties/{prop_id}/room-types",
        json={
            "name": "Standard",
            "count": 10,
            "base_capacity": 2,
            "max_capacity": 4,
            "default_rate": 100.00,
        },
    )
    assert response.status_code == 201
    rt_id = response.json()["id"]

    # Create package
    response = await client.post(
        f"/api/v1/properties/{prop_id}/packages",
        json={"name": "Comp Package API", "base_price": "500.00"},
    )
    assert response.status_code == 201
    pkg_id = response.json()["id"]

    # Create composition
    response = await client.post(
        f"/api/v1/packages/{pkg_id}/compositions",
        json={"room_type_id": str(rt_id), "quantity": 2, "nights": 3},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["room_type_id"] == rt_id
    assert data["quantity"] == 2
    assert data["nights"] == 3
    comp_id = data["id"]

    # List compositions
    response = await client.get(f"/api/v1/packages/{pkg_id}/compositions")
    assert response.status_code == 200
    items = response.json()
    assert any(i["id"] == comp_id for i in items)

    # Update composition
    response = await client.patch(
        f"/api/v1/packages/compositions/{comp_id}",
        json={"quantity": 5},
    )
    assert response.status_code == 200
    assert response.json()["quantity"] == 5

    # Delete composition
    response = await client.delete(f"/api/v1/packages/compositions/{comp_id}")
    assert response.status_code == 204

    # Verify deletion by listing under package
    response = await client.get(f"/api/v1/packages/{pkg_id}/compositions")
    assert response.status_code == 200
    items = response.json()
    assert not any(i["id"] == comp_id for i in items)


@pytest.mark.asyncio
async def test_package_add_on_api_crud(client: AsyncClient):
    # Create property and package
    response = await client.post(
        "/api/v1/properties/",
        json={"name": "AddOn API Hotel"},
    )
    assert response.status_code == 201
    prop_id = response.json()["id"]

    response = await client.post(
        f"/api/v1/properties/{prop_id}/packages",
        json={"name": "AddOn Package API", "base_price": "300.00"},
    )
    assert response.status_code == 201
    pkg_id = response.json()["id"]

    # Create real add-on
    response = await client.post(
        "/api/v1/add-ons/",
        json={"property_id": prop_id, "name": "Spa", "type": "day", "unit_price": "50.00"},
    )
    assert response.status_code == 201
    add_on_id = response.json()["id"]

    # Create add-on link
    response = await client.post(
        f"/api/v1/packages/{pkg_id}/add-ons",
        json={"add_on_id": add_on_id, "quantity": 2, "is_included": True},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["add_on_id"] == add_on_id
    assert data["quantity"] == 2
    assert data["is_included"] is True
    pao_id = data["id"]

    # List add-ons
    response = await client.get(f"/api/v1/packages/{pkg_id}/add-ons")
    assert response.status_code == 200
    items = response.json()
    assert any(i["id"] == pao_id for i in items)

    # Update add-on link
    response = await client.patch(
        f"/api/v1/packages/add-ons/{pao_id}",
        json={"quantity": 4, "is_included": False},
    )
    assert response.status_code == 200
    assert response.json()["quantity"] == 4
    assert response.json()["is_included"] is False

    # Delete add-on link
    response = await client.delete(f"/api/v1/packages/add-ons/{pao_id}")
    assert response.status_code == 204

    # Verify deletion by listing under package
    response = await client.get(f"/api/v1/packages/{pkg_id}/add-ons")
    assert response.status_code == 200
    items = response.json()
    assert not any(i["id"] == pao_id for i in items)


@pytest.mark.asyncio
async def test_package_not_found(client: AsyncClient):
    fake_id = str(uuid.uuid4())

    response = await client.get(f"/api/v1/packages/{fake_id}")
    assert response.status_code == 404

    response = await client.patch(f"/api/v1/packages/{fake_id}", json={"name": "X"})
    assert response.status_code == 404

    response = await client.delete(f"/api/v1/packages/{fake_id}")
    assert response.status_code == 404

    response = await client.get(f"/api/v1/packages/{fake_id}/compositions")
    assert response.status_code == 404

    response = await client.post(
        f"/api/v1/packages/{fake_id}/compositions",
        json={"room_type_id": str(uuid.uuid4()), "quantity": 1},
    )
    assert response.status_code == 404

    response = await client.get(f"/api/v1/packages/{fake_id}/add-ons")
    assert response.status_code == 404

    response = await client.post(
        f"/api/v1/packages/{fake_id}/add-ons",
        json={"add_on_id": str(uuid.uuid4()), "quantity": 1},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_package_property_not_found(client: AsyncClient):
    fake_id = str(uuid.uuid4())

    response = await client.post(
        f"/api/v1/properties/{fake_id}/packages",
        json={"name": "Ghost Package", "base_price": "100.00"},
    )
    assert response.status_code == 404

    response = await client.get(f"/api/v1/properties/{fake_id}/packages")
    assert response.status_code == 404
