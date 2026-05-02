import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.organization import Organization
from app.repositories.organization import OrganizationRepository
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationRead,
    OrganizationUpdate,
)

router = APIRouter()


@router.get("/", response_model=List[OrganizationRead])
async def list_organizations(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> List[Organization]:
    repo = OrganizationRepository(db)
    return await repo.get_multi(skip=skip, limit=limit)


@router.post("/", response_model=OrganizationRead, status_code=201)
async def create_organization(
    data: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
) -> Organization:
    repo = OrganizationRepository(db)
    return await repo.create(data.model_dump())


@router.get("/{organization_id}", response_model=OrganizationRead)
async def get_organization(
    organization_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Organization:
    repo = OrganizationRepository(db)
    org = await repo.get(organization_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.patch("/{organization_id}", response_model=OrganizationRead)
async def update_organization(
    organization_id: uuid.UUID,
    data: OrganizationUpdate,
    db: AsyncSession = Depends(get_db),
) -> Organization:
    repo = OrganizationRepository(db)
    org = await repo.get(organization_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    update_data = data.model_dump(exclude_unset=True)
    return await repo.update(org, update_data)


@router.delete("/{organization_id}", status_code=204)
async def delete_organization(
    organization_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    repo = OrganizationRepository(db)
    org = await repo.get(organization_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    await repo.delete(org)
