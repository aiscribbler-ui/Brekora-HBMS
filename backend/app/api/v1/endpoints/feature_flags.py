import uuid
from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.models.feature_flag import FeatureFlag
from app.repositories.feature_flag import FeatureFlagRepository
from app.schemas.feature_flag import FeatureFlagCreate, FeatureFlagRead, FeatureFlagUpdate

router = APIRouter()
settings = get_settings()
DEFAULT_ORG_ID = settings.DEFAULT_ORG_ID if hasattr(settings, "DEFAULT_ORG_ID") else None


def get_org_id(x_org_id: str | None = Header(default=None, alias="X-Org-ID")) -> uuid.UUID:
    if x_org_id:
        return uuid.UUID(x_org_id)
    if DEFAULT_ORG_ID:
        return DEFAULT_ORG_ID
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.get("/", response_model=List[FeatureFlagRead])
async def list_feature_flags(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> List[FeatureFlag]:
    repo = FeatureFlagRepository(db, org_id)
    return await repo.get_multi(skip=skip, limit=limit)


@router.post("/", response_model=FeatureFlagRead, status_code=201)
async def create_feature_flag(
    data: FeatureFlagCreate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> FeatureFlag:
    repo = FeatureFlagRepository(db, org_id)
    obj_in = data.model_dump(exclude_unset=True)
    if "org_id" in obj_in and obj_in["org_id"] is None:
        del obj_in["org_id"]
    return await repo.create(obj_in)


@router.get("/{flag_id}", response_model=FeatureFlagRead)
async def get_feature_flag(
    flag_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> FeatureFlag:
    repo = FeatureFlagRepository(db, org_id)
    flag = await repo.get(flag_id)
    if not flag:
        raise HTTPException(status_code=404, detail="Feature flag not found")
    return flag


@router.patch("/{flag_id}", response_model=FeatureFlagRead)
async def update_feature_flag(
    flag_id: uuid.UUID,
    data: FeatureFlagUpdate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> FeatureFlag:
    repo = FeatureFlagRepository(db, org_id)
    flag = await repo.get(flag_id)
    if not flag:
        raise HTTPException(status_code=404, detail="Feature flag not found")
    update_data = data.model_dump(exclude_unset=True)
    return await repo.update(flag, update_data)


@router.delete("/{flag_id}", status_code=204)
async def delete_feature_flag(
    flag_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> None:
    repo = FeatureFlagRepository(db, org_id)
    flag = await repo.get(flag_id)
    if not flag:
        raise HTTPException(status_code=404, detail="Feature flag not found")
    await repo.delete(flag)


@router.get("/check/{key}", response_model=dict)
async def check_feature_flag(
    key: str,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> dict:
    repo = FeatureFlagRepository(db, org_id)
    flag = await repo.get_by_key(key)
    if not flag:
        return {"enabled": False, "value": None}
    return {"enabled": flag.enabled, "value": flag.value}
