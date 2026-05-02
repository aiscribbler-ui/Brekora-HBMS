import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.repositories.ota_settings import OTASettingsRepository
from app.schemas.ota_settings import OTASettingsCreate, OTASettingsRead, OTASettingsUpdate

router = APIRouter()
settings = get_settings()
DEFAULT_ORG_ID = settings.DEFAULT_ORG_ID


def get_org_id(
    x_org_id: str | None = Header(default=None, alias="X-Org-ID"),
) -> uuid.UUID:
    if x_org_id:
        return uuid.UUID(x_org_id)
    return DEFAULT_ORG_ID


@router.get("/", response_model=list[OTASettingsRead])
async def list_ota_settings(
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> list[OTASettingsRead]:
    repo = OTASettingsRepository(db, org_id)
    return await repo.get_multi()


@router.put("/", response_model=OTASettingsRead)
async def upsert_ota_settings(
    data: OTASettingsCreate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> Any:
    repo = OTASettingsRepository(db, org_id)
    existing = await repo.get_by_ota_source(data.ota_source)
    if existing:
        update_data = data.model_dump(exclude_unset=True, exclude={"ota_source"})
        updated = await repo.update(existing, update_data)
        return updated
    return await repo.create(data.model_dump())
