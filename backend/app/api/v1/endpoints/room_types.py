import uuid
from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.models.room_type import RoomType
from app.repositories.room_type import RoomTypeRepository
from app.schemas.room_type import RoomTypeRead, RoomTypeUpdate

router = APIRouter()

settings = get_settings()
DEFAULT_ORG_ID = settings.DEFAULT_ORG_ID if hasattr(settings, "DEFAULT_ORG_ID") else None


def get_org_id(x_org_id: str | None = Header(default=None, alias="X-Org-ID")) -> uuid.UUID:
    if x_org_id:
        return uuid.UUID(x_org_id)
    if DEFAULT_ORG_ID:
        return DEFAULT_ORG_ID
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.get("/{room_type_id}", response_model=RoomTypeRead)
async def get_room_type(
    room_type_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> RoomType:
    repo = RoomTypeRepository(db, org_id)
    rt = await repo.get(room_type_id)
    if not rt or rt.is_archived:
        raise HTTPException(status_code=404, detail="Room type not found")
    return rt


@router.patch("/{room_type_id}", response_model=RoomTypeRead)
async def update_room_type(
    room_type_id: uuid.UUID,
    data: RoomTypeUpdate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> RoomType:
    repo = RoomTypeRepository(db, org_id)
    rt = await repo.get(room_type_id)
    if not rt or rt.is_archived:
        raise HTTPException(status_code=404, detail="Room type not found")
    update_data = data.model_dump(exclude_unset=True)
    return await repo.update(rt, update_data)


@router.delete("/{room_type_id}", status_code=204)
async def delete_room_type(
    room_type_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> None:
    repo = RoomTypeRepository(db, org_id)
    rt = await repo.get(room_type_id)
    if not rt:
        raise HTTPException(status_code=404, detail="Room type not found")
    await repo.update(rt, {"is_archived": True, "is_active": False})
