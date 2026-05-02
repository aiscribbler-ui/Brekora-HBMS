import uuid
from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.models.ota_mapping import OTAMapping
from app.repositories.ota_mapping import OTAMappingRepository
from app.repositories.property import PropertyRepository
from app.repositories.room_type import RoomTypeRepository
from app.schemas.ota_mapping import OTAMappingCreate, OTAMappingRead, OTAMappingUpdate

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


@router.get("/", response_model=List[OTAMappingRead])
async def list_ota_mappings(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> List[OTAMapping]:
    repo = OTAMappingRepository(db, org_id)
    return await repo.get_multi(skip=skip, limit=limit)


@router.post("/", response_model=OTAMappingRead, status_code=201)
async def create_ota_mapping(
    data: OTAMappingCreate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> OTAMapping:
    prop_repo = PropertyRepository(db, org_id)
    prop = await prop_repo.get(data.property_id)
    if not prop or prop.is_archived:
        raise HTTPException(status_code=404, detail="Property not found")

    rt_repo = RoomTypeRepository(db, org_id)
    rt = await rt_repo.get(data.room_type_id)
    if not rt or rt.is_archived:
        raise HTTPException(status_code=404, detail="Room type not found")

    repo = OTAMappingRepository(db, org_id)
    obj_in = data.model_dump(exclude_unset=True)
    if "org_id" in obj_in and obj_in["org_id"] is None:
        del obj_in["org_id"]
    try:
        return await repo.create(obj_in)
    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="OTA mapping already exists for this org, source and listing",
        )


@router.get("/{mapping_id}", response_model=OTAMappingRead)
async def get_ota_mapping(
    mapping_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> OTAMapping:
    repo = OTAMappingRepository(db, org_id)
    mapping = await repo.get(mapping_id)
    if not mapping or mapping.is_archived:
        raise HTTPException(status_code=404, detail="OTA mapping not found")
    return mapping


@router.patch("/{mapping_id}", response_model=OTAMappingRead)
async def update_ota_mapping(
    mapping_id: uuid.UUID,
    data: OTAMappingUpdate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> OTAMapping:
    repo = OTAMappingRepository(db, org_id)
    mapping = await repo.get(mapping_id)
    if not mapping or mapping.is_archived:
        raise HTTPException(status_code=404, detail="OTA mapping not found")

    update_data = data.model_dump(exclude_unset=True)

    if "property_id" in update_data:
        prop_repo = PropertyRepository(db, org_id)
        prop = await prop_repo.get(update_data["property_id"])
        if not prop or prop.is_archived:
            raise HTTPException(status_code=404, detail="Property not found")

    if "room_type_id" in update_data:
        rt_repo = RoomTypeRepository(db, org_id)
        rt = await rt_repo.get(update_data["room_type_id"])
        if not rt or rt.is_archived:
            raise HTTPException(status_code=404, detail="Room type not found")

    return await repo.update(mapping, update_data)


@router.delete("/{mapping_id}", status_code=204)
async def delete_ota_mapping(
    mapping_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> None:
    repo = OTAMappingRepository(db, org_id)
    mapping = await repo.get(mapping_id)
    if not mapping:
        raise HTTPException(status_code=404, detail="OTA mapping not found")
    await repo.update(mapping, {"is_archived": True, "is_active": False})
