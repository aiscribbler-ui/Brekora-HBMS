import uuid
from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.models.package import Package, PackageAddOn, PackageComposition
from app.repositories.package import (
    PackageAddOnRepository,
    PackageCompositionRepository,
    PackageRepository,
)
from app.repositories.property import PropertyRepository
from app.schemas.package import (
    PackageAddOnCreate,
    PackageAddOnRead,
    PackageAddOnUpdate,
    PackageCompositionCreate,
    PackageCompositionRead,
    PackageCompositionUpdate,
    PackageCreate,
    PackageRead,
    PackageUpdate,
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


# Standalone Package endpoints


@router.get("/", response_model=List[PackageRead])
async def list_packages(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> List[Package]:
    repo = PackageRepository(db, org_id)
    return await repo.get_multi(skip=skip, limit=limit)


@router.post("/", response_model=PackageRead, status_code=201)
async def create_package(
    data: PackageCreate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> Package:
    prop_repo = PropertyRepository(db, org_id)
    prop = await prop_repo.get(data.property_id)
    if not prop or prop.is_archived:
        raise HTTPException(status_code=404, detail="Property not found")

    repo = PackageRepository(db, org_id)
    obj_in = data.model_dump(exclude_unset=True)
    if "org_id" in obj_in and obj_in["org_id"] is None:
        del obj_in["org_id"]
    return await repo.create(obj_in)


@router.get("/{package_id}", response_model=PackageRead)
async def get_package(
    package_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> Package:
    repo = PackageRepository(db, org_id)
    pkg = await repo.get(package_id)
    if not pkg or pkg.is_archived:
        raise HTTPException(status_code=404, detail="Package not found")
    return pkg


@router.patch("/{package_id}", response_model=PackageRead)
async def update_package(
    package_id: uuid.UUID,
    data: PackageUpdate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> Package:
    repo = PackageRepository(db, org_id)
    pkg = await repo.get(package_id)
    if not pkg or pkg.is_archived:
        raise HTTPException(status_code=404, detail="Package not found")
    update_data = data.model_dump(exclude_unset=True)
    return await repo.update(pkg, update_data)


@router.delete("/{package_id}", status_code=204)
async def delete_package(
    package_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> None:
    repo = PackageRepository(db, org_id)
    pkg = await repo.get(package_id)
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")
    await repo.update(pkg, {"is_archived": True, "is_active": False})


# PackageComposition nested endpoints


@router.get("/{package_id}/compositions", response_model=List[PackageCompositionRead])
async def list_package_compositions(
    package_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> List[PackageComposition]:
    pkg_repo = PackageRepository(db, org_id)
    pkg = await pkg_repo.get(package_id)
    if not pkg or pkg.is_archived:
        raise HTTPException(status_code=404, detail="Package not found")

    repo = PackageCompositionRepository(db, org_id)
    return await repo.get_multi_by_package(package_id, skip=skip, limit=limit)


@router.post(
    "/{package_id}/compositions", response_model=PackageCompositionRead, status_code=201
)
async def create_package_composition(
    package_id: uuid.UUID,
    data: PackageCompositionCreate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> PackageComposition:
    pkg_repo = PackageRepository(db, org_id)
    pkg = await pkg_repo.get(package_id)
    if not pkg or pkg.is_archived:
        raise HTTPException(status_code=404, detail="Package not found")

    repo = PackageCompositionRepository(db, org_id)
    obj_in = data.model_dump(exclude_unset=True)
    obj_in["package_id"] = package_id
    if "org_id" in obj_in and obj_in["org_id"] is None:
        del obj_in["org_id"]
    return await repo.create(obj_in)


# PackageAddOn nested endpoints


@router.get("/{package_id}/add-ons", response_model=List[PackageAddOnRead])
async def list_package_add_ons(
    package_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> List[PackageAddOn]:
    pkg_repo = PackageRepository(db, org_id)
    pkg = await pkg_repo.get(package_id)
    if not pkg or pkg.is_archived:
        raise HTTPException(status_code=404, detail="Package not found")

    repo = PackageAddOnRepository(db, org_id)
    return await repo.get_multi_by_package(package_id, skip=skip, limit=limit)


@router.post("/{package_id}/add-ons", response_model=PackageAddOnRead, status_code=201)
async def create_package_add_on(
    package_id: uuid.UUID,
    data: PackageAddOnCreate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> PackageAddOn:
    pkg_repo = PackageRepository(db, org_id)
    pkg = await pkg_repo.get(package_id)
    if not pkg or pkg.is_archived:
        raise HTTPException(status_code=404, detail="Package not found")

    repo = PackageAddOnRepository(db, org_id)
    obj_in = data.model_dump(exclude_unset=True)
    obj_in["package_id"] = package_id
    if "org_id" in obj_in and obj_in["org_id"] is None:
        del obj_in["org_id"]
    return await repo.create(obj_in)


# Standalone composition / add-on update & delete


@router.patch(
    "/compositions/{composition_id}", response_model=PackageCompositionRead
)
async def update_package_composition(
    composition_id: uuid.UUID,
    data: PackageCompositionUpdate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> PackageComposition:
    repo = PackageCompositionRepository(db, org_id)
    comp = await repo.get(composition_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Package composition not found")
    update_data = data.model_dump(exclude_unset=True)
    return await repo.update(comp, update_data)


@router.delete("/compositions/{composition_id}", status_code=204)
async def delete_package_composition(
    composition_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> None:
    repo = PackageCompositionRepository(db, org_id)
    comp = await repo.get(composition_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Package composition not found")
    await repo.delete(comp)


@router.patch("/add-ons/{add_on_id}", response_model=PackageAddOnRead)
async def update_package_add_on(
    add_on_id: uuid.UUID,
    data: PackageAddOnUpdate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> PackageAddOn:
    repo = PackageAddOnRepository(db, org_id)
    pao = await repo.get(add_on_id)
    if not pao:
        raise HTTPException(status_code=404, detail="Package add-on not found")
    update_data = data.model_dump(exclude_unset=True)
    return await repo.update(pao, update_data)


@router.delete("/add-ons/{add_on_id}", status_code=204)
async def delete_package_add_on(
    add_on_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> None:
    repo = PackageAddOnRepository(db, org_id)
    pao = await repo.get(add_on_id)
    if not pao:
        raise HTTPException(status_code=404, detail="Package add-on not found")
    await repo.delete(pao)
