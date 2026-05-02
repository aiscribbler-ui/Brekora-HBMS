import uuid
from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.models.inventory_buffer import InventoryBuffer
from app.repositories.inventory_buffer import InventoryBufferRepository
from app.schemas.inventory_buffer import InventoryBufferCreate, InventoryBufferRead, InventoryBufferUpdate

router = APIRouter()
settings = get_settings()
DEFAULT_ORG_ID = settings.DEFAULT_ORG_ID if hasattr(settings, "DEFAULT_ORG_ID") else None


def get_org_id(x_org_id: str | None = Header(default=None, alias="X-Org-ID")) -> uuid.UUID:
    if x_org_id:
        return uuid.UUID(x_org_id)
    if DEFAULT_ORG_ID:
        return DEFAULT_ORG_ID
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.get("/", response_model=List[InventoryBufferRead])
async def list_inventory_buffers(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> List[InventoryBuffer]:
    repo = InventoryBufferRepository(db, org_id)
    return await repo.get_multi(skip=skip, limit=limit)


@router.post("/", response_model=InventoryBufferRead, status_code=201)
async def create_inventory_buffer(
    data: InventoryBufferCreate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> InventoryBuffer:
    repo = InventoryBufferRepository(db, org_id)
    obj_in = data.model_dump(exclude_unset=True)
    if "org_id" in obj_in and obj_in["org_id"] is None:
        del obj_in["org_id"]
    return await repo.create(obj_in)


@router.get("/{buffer_id}", response_model=InventoryBufferRead)
async def get_inventory_buffer(
    buffer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> InventoryBuffer:
    repo = InventoryBufferRepository(db, org_id)
    buf = await repo.get(buffer_id)
    if not buf:
        raise HTTPException(status_code=404, detail="Inventory buffer not found")
    return buf


@router.patch("/{buffer_id}", response_model=InventoryBufferRead)
async def update_inventory_buffer(
    buffer_id: uuid.UUID,
    data: InventoryBufferUpdate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> InventoryBuffer:
    repo = InventoryBufferRepository(db, org_id)
    buf = await repo.get(buffer_id)
    if not buf:
        raise HTTPException(status_code=404, detail="Inventory buffer not found")
    update_data = data.model_dump(exclude_unset=True)
    return await repo.update(buf, update_data)


@router.delete("/{buffer_id}", status_code=204)
async def delete_inventory_buffer(
    buffer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> None:
    repo = InventoryBufferRepository(db, org_id)
    buf = await repo.get(buffer_id)
    if not buf:
        raise HTTPException(status_code=404, detail="Inventory buffer not found")
    await repo.delete(buf)
