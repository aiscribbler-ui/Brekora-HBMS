import os
import uuid
from typing import List

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.property import Property
from app.models.room_type import RoomType
from app.models.user import User
from app.repositories.package import PackageRepository
from app.repositories.property import PropertyRepository
from app.repositories.room_type import RoomTypeRepository
from app.schemas.package import PackageBase, PackageCreate, PackageRead
from app.schemas.property import PropertyCreate, PropertyRead, PropertyUpdate
from app.schemas.room_type import RoomTypeCreate, RoomTypeRead

router = APIRouter()

settings = get_settings()
DEFAULT_ORG_ID = settings.DEFAULT_ORG_ID
UPLOAD_DIR = settings.UPLOAD_DIR
os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_org_id(x_org_id: str | None = Header(default=None, alias="X-Org-ID")) -> uuid.UUID:
    if x_org_id:
        return uuid.UUID(x_org_id)
    return DEFAULT_ORG_ID


@router.get("/", response_model=List[PropertyRead], dependencies=[])
async def list_properties(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> List[Property]:
    repo = PropertyRepository(db, org_id)
    return await repo.get_multi(skip=skip, limit=limit)


@router.post("/", response_model=PropertyRead, status_code=201)
async def create_property(
    data: PropertyCreate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
    current_user: User = Depends(get_current_user),
) -> Property:
    repo = PropertyRepository(db, org_id)
    obj_in = data.model_dump(exclude_unset=True)
    if "org_id" in obj_in and obj_in["org_id"] is None:
        del obj_in["org_id"]
    return await repo.create(obj_in)


@router.get("/{property_id}", response_model=PropertyRead, dependencies=[])
async def get_property(
    property_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> Property:
    repo = PropertyRepository(db, org_id)
    prop = await repo.get(property_id)
    if not prop or prop.is_archived:
        raise HTTPException(status_code=404, detail="Property not found")
    return prop


@router.patch("/{property_id}", response_model=PropertyRead)
async def update_property(
    property_id: uuid.UUID,
    data: PropertyUpdate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
    current_user: User = Depends(get_current_user),
) -> Property:
    repo = PropertyRepository(db, org_id)
    prop = await repo.get(property_id)
    if not prop or prop.is_archived:
        raise HTTPException(status_code=404, detail="Property not found")
    update_data = data.model_dump(exclude_unset=True)
    return await repo.update(prop, update_data)


@router.delete("/{property_id}", status_code=204)
async def delete_property(
    property_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
    current_user: User = Depends(get_current_user),
) -> None:
    repo = PropertyRepository(db, org_id)
    prop = await repo.get(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    await repo.update(prop, {"is_archived": True, "is_active": False})


@router.get("/{property_id}/room-types", response_model=List[RoomTypeRead])
async def list_room_types(
    property_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
    current_user: User = Depends(get_current_user),
) -> List[RoomType]:
    repo = RoomTypeRepository(db, org_id)
    return await repo.get_multi_by_property(property_id, skip=skip, limit=limit)


@router.post("/{property_id}/room-types", response_model=RoomTypeRead, status_code=201)
async def create_room_type(
    property_id: uuid.UUID,
    data: RoomTypeCreate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
    current_user: User = Depends(get_current_user),
) -> RoomType:
    prop_repo = PropertyRepository(db, org_id)
    prop = await prop_repo.get(property_id)
    if not prop or prop.is_archived:
        raise HTTPException(status_code=404, detail="Property not found")

    repo = RoomTypeRepository(db, org_id)
    obj_in = data.model_dump(exclude_unset=True)
    obj_in["property_id"] = property_id
    if "org_id" in obj_in and obj_in["org_id"] is None:
        del obj_in["org_id"]
    return await repo.create(obj_in)


@router.post("/{property_id}/photos", status_code=201)
async def upload_property_photos(
    property_id: uuid.UUID,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
    current_user: User = Depends(get_current_user),
) -> dict:
    repo = PropertyRepository(db, org_id)
    prop = await repo.get(property_id)
    if not prop or prop.is_archived:
        raise HTTPException(status_code=404, detail="Property not found")

    photos = prop.photos or []
    for file in files:
        ext = os.path.splitext(file.filename or "")[1]
        filename = f"{uuid.uuid4()}{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(await file.read())
        photos.append({
            "filename": file.filename,
            "path": f"/uploads/{filename}",
            "url": f"/uploads/{filename}",
            "caption": file.filename,
        })

    updated = await repo.update(prop, {"photos": photos})
    return {"photos": updated.photos or []}


@router.get("/{property_id}/packages", response_model=List[PackageRead])
async def list_property_packages(
    property_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
    current_user: User = Depends(get_current_user),
) -> List[PackageRead]:
    prop_repo = PropertyRepository(db, org_id)
    prop = await prop_repo.get(property_id)
    if not prop or prop.is_archived:
        raise HTTPException(status_code=404, detail="Property not found")

    repo = PackageRepository(db, org_id)
    return await repo.get_multi_by_property(property_id, skip=skip, limit=limit)


@router.post("/{property_id}/packages", response_model=PackageRead, status_code=201)
async def create_property_package(
    property_id: uuid.UUID,
    data: PackageBase,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
    current_user: User = Depends(get_current_user),
) -> PackageRead:
    prop_repo = PropertyRepository(db, org_id)
    prop = await prop_repo.get(property_id)
    if not prop or prop.is_archived:
        raise HTTPException(status_code=404, detail="Property not found")

    repo = PackageRepository(db, org_id)
    obj_in = data.model_dump(exclude_unset=True)
    obj_in["property_id"] = property_id
    if "org_id" in obj_in and obj_in["org_id"] is None:
        del obj_in["org_id"]
    return await repo.create(obj_in)
