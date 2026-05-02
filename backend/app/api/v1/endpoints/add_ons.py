import uuid
from datetime import timedelta
from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.models.add_on import AddOn, AddOnType
from app.models.add_on_capacity import AddOnCapacity
from app.repositories.add_on import AddOnCapacityRepository, AddOnRepository
from app.repositories.property import PropertyRepository
from app.schemas.add_on import (
    AddOnCapacityCreate,
    AddOnCapacityRead,
    AddOnCapacityUpdate,
    AddOnCreate,
    AddOnRead,
    AddOnUpdate,
    GenerateCapacityRequest,
)

router = APIRouter()

settings = get_settings()
DEFAULT_ORG_ID = (
    settings.DEFAULT_ORG_ID if hasattr(settings, "DEFAULT_ORG_ID") else None
)


def get_org_id(
    x_org_id: str | None = Header(default=None, alias="X-Org-ID"),
) -> uuid.UUID:
    if x_org_id:
        return uuid.UUID(x_org_id)
    if DEFAULT_ORG_ID:
        return DEFAULT_ORG_ID
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.get("/", response_model=List[AddOnRead])
async def list_add_ons(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> List[AddOn]:
    repo = AddOnRepository(db, org_id)
    return await repo.get_multi(skip=skip, limit=limit)


@router.post("/", response_model=AddOnRead, status_code=201)
async def create_add_on(
    data: AddOnCreate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> AddOn:
    prop_repo = PropertyRepository(db, org_id)
    prop = await prop_repo.get(data.property_id)
    if not prop or prop.is_archived:
        raise HTTPException(status_code=404, detail="Property not found")

    repo = AddOnRepository(db, org_id)
    obj_in = data.model_dump(exclude_unset=True)
    if "org_id" in obj_in and obj_in["org_id"] is None:
        del obj_in["org_id"]
    return await repo.create(obj_in)


@router.get("/{add_on_id}", response_model=AddOnRead)
async def get_add_on(
    add_on_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> AddOn:
    repo = AddOnRepository(db, org_id)
    addon = await repo.get(add_on_id)
    if not addon or addon.is_archived:
        raise HTTPException(status_code=404, detail="Add-on not found")
    return addon


@router.patch("/{add_on_id}", response_model=AddOnRead)
async def update_add_on(
    add_on_id: uuid.UUID,
    data: AddOnUpdate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> AddOn:
    repo = AddOnRepository(db, org_id)
    addon = await repo.get(add_on_id)
    if not addon or addon.is_archived:
        raise HTTPException(status_code=404, detail="Add-on not found")
    update_data = data.model_dump(exclude_unset=True)
    return await repo.update(addon, update_data)


@router.delete("/{add_on_id}", status_code=204)
async def delete_add_on(
    add_on_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> None:
    repo = AddOnRepository(db, org_id)
    addon = await repo.get(add_on_id)
    if not addon:
        raise HTTPException(status_code=404, detail="Add-on not found")
    await repo.update(addon, {"is_archived": True, "is_active": False})


# Capacity nested endpoints


@router.get("/{add_on_id}/capacity", response_model=List[AddOnCapacityRead])
async def list_add_on_capacities(
    add_on_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> List[AddOnCapacity]:
    repo = AddOnRepository(db, org_id)
    addon = await repo.get(add_on_id)
    if not addon or addon.is_archived:
        raise HTTPException(status_code=404, detail="Add-on not found")

    cap_repo = AddOnCapacityRepository(db)
    return await cap_repo.get_multi_by_add_on(add_on_id, skip=skip, limit=limit)


@router.post(
    "/{add_on_id}/capacity", response_model=AddOnCapacityRead, status_code=201
)
async def create_add_on_capacity(
    add_on_id: uuid.UUID,
    data: AddOnCapacityCreate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> AddOnCapacity:
    repo = AddOnRepository(db, org_id)
    addon = await repo.get(add_on_id)
    if not addon or addon.is_archived:
        raise HTTPException(status_code=404, detail="Add-on not found")

    cap_repo = AddOnCapacityRepository(db)
    obj_in = data.model_dump(exclude_unset=True)
    obj_in["add_on_id"] = add_on_id
    return await cap_repo.create(obj_in)


@router.post(
    "/{add_on_id}/generate-capacity",
    response_model=List[AddOnCapacityRead],
    status_code=201,
)
async def generate_capacity(
    add_on_id: uuid.UUID,
    data: GenerateCapacityRequest,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> List[AddOnCapacity]:
    repo = AddOnRepository(db, org_id)
    addon = await repo.get(add_on_id)
    if not addon or addon.is_archived:
        raise HTTPException(status_code=404, detail="Add-on not found")

    if data.end_date < data.start_date:
        raise HTTPException(
            status_code=400, detail="end_date must be >= start_date"
        )

    if addon.type == AddOnType.package_instance:
        raise HTTPException(
            status_code=400,
            detail="package_instance add-ons do not need capacity records",
        )

    cap_repo = AddOnCapacityRepository(db)
    created: List[AddOnCapacity] = []

    if addon.type == AddOnType.slot:
        if not data.slot_times:
            raise HTTPException(
                status_code=400,
                detail="slot_times required for slot-based add-ons",
            )
        for n in range((data.end_date - data.start_date).days + 1):
            d = data.start_date + timedelta(days=n)
            for st in data.slot_times:
                existing = await cap_repo.get_by_add_on_date_slot(addon.id, d, st)
                if existing:
                    continue
                rec = await cap_repo.create(
                    {
                        "add_on_id": addon.id,
                        "date": d,
                        "slot_time": st,
                        "available_capacity": addon.default_capacity,
                        "total_capacity": addon.default_capacity,
                    }
                )
                created.append(rec)
    else:
        # day-based
        for n in range((data.end_date - data.start_date).days + 1):
            d = data.start_date + timedelta(days=n)
            existing = await cap_repo.get_by_add_on_date(addon.id, d)
            if existing:
                continue
            rec = await cap_repo.create(
                {
                    "add_on_id": addon.id,
                    "date": d,
                    "slot_time": None,
                    "available_capacity": addon.default_capacity,
                    "total_capacity": addon.default_capacity,
                }
            )
            created.append(rec)

    return created


# Standalone capacity read, update & delete


@router.get("/capacity/{capacity_id}", response_model=AddOnCapacityRead)
async def get_add_on_capacity(
    capacity_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> AddOnCapacity:
    cap_repo = AddOnCapacityRepository(db)
    cap = await cap_repo.get(capacity_id)
    if not cap:
        raise HTTPException(status_code=404, detail="Capacity record not found")

    # Verify add-on belongs to org
    addon_repo = AddOnRepository(db, org_id)
    addon = await addon_repo.get(cap.add_on_id)
    if not addon or addon.is_archived:
        raise HTTPException(status_code=404, detail="Add-on not found")

    return cap


@router.patch("/capacity/{capacity_id}", response_model=AddOnCapacityRead)
async def update_add_on_capacity(
    capacity_id: uuid.UUID,
    data: AddOnCapacityUpdate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> AddOnCapacity:
    cap_repo = AddOnCapacityRepository(db)
    cap = await cap_repo.get(capacity_id)
    if not cap:
        raise HTTPException(status_code=404, detail="Capacity record not found")

    # Verify add-on belongs to org
    addon_repo = AddOnRepository(db, org_id)
    addon = await addon_repo.get(cap.add_on_id)
    if not addon or addon.is_archived:
        raise HTTPException(status_code=404, detail="Add-on not found")

    update_data = data.model_dump(exclude_unset=True)
    return await cap_repo.update(cap, update_data)


@router.delete("/capacity/{capacity_id}", status_code=204)
async def delete_add_on_capacity(
    capacity_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> None:
    cap_repo = AddOnCapacityRepository(db)
    cap = await cap_repo.get(capacity_id)
    if not cap:
        raise HTTPException(status_code=404, detail="Capacity record not found")

    # Verify add-on belongs to org
    addon_repo = AddOnRepository(db, org_id)
    addon = await addon_repo.get(cap.add_on_id)
    if not addon or addon.is_archived:
        raise HTTPException(status_code=404, detail="Add-on not found")

    await cap_repo.delete(cap)
