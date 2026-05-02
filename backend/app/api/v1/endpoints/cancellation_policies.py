import uuid
from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.models.cancellation_policy import CancellationPolicy
from app.repositories.cancellation_policy import CancellationPolicyRepository
from app.schemas.cancellation_policy import (
    CancellationPolicyCreate,
    CancellationPolicyRead,
    CancellationPolicyUpdate,
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


@router.get("/", response_model=List[CancellationPolicyRead])
async def list_cancellation_policies(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> List[CancellationPolicy]:
    repo = CancellationPolicyRepository(db, org_id)
    return await repo.get_multi(skip=skip, limit=limit)


@router.post("/", response_model=CancellationPolicyRead, status_code=201)
async def create_cancellation_policy(
    data: CancellationPolicyCreate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> CancellationPolicy:
    repo = CancellationPolicyRepository(db, org_id)
    obj_in = data.model_dump(exclude_unset=True)
    if "org_id" in obj_in and obj_in["org_id"] is None:
        del obj_in["org_id"]
    return await repo.create(obj_in)


@router.get("/{policy_id}", response_model=CancellationPolicyRead)
async def get_cancellation_policy(
    policy_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> CancellationPolicy:
    repo = CancellationPolicyRepository(db, org_id)
    policy = await repo.get(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Cancellation policy not found")
    return policy


@router.patch("/{policy_id}", response_model=CancellationPolicyRead)
async def update_cancellation_policy(
    policy_id: uuid.UUID,
    data: CancellationPolicyUpdate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> CancellationPolicy:
    repo = CancellationPolicyRepository(db, org_id)
    policy = await repo.get(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Cancellation policy not found")
    update_data = data.model_dump(exclude_unset=True)
    return await repo.update(policy, update_data)


@router.delete("/{policy_id}", status_code=204)
async def delete_cancellation_policy(
    policy_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> None:
    repo = CancellationPolicyRepository(db, org_id)
    policy = await repo.get(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Cancellation policy not found")
    await repo.delete(policy)
