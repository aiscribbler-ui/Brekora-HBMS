import uuid
from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.db.session import get_db
from app.models.user import User
from app.repositories.role import RoleRepository
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserRead, UserUpdate

router = APIRouter()

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def get_org_id(x_org_id: str | None = Header(default=None, alias="X-Org-ID")) -> uuid.UUID:
    if x_org_id:
        return uuid.UUID(x_org_id)
    return DEFAULT_ORG_ID


@router.get("/", response_model=List[UserRead])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> List[User]:
    repo = UserRepository(db, org_id)
    return await repo.get_multi(skip=skip, limit=limit)


@router.post("/", response_model=UserRead, status_code=201)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> User:
    repo = UserRepository(db, org_id)
    obj_in = data.model_dump(exclude_unset=True)
    password = obj_in.pop("password", None)
    if "org_id" in obj_in and obj_in["org_id"] is None:
        del obj_in["org_id"]

    if password:
        obj_in["password_hash"] = get_password_hash(password)

    if obj_in.get("role_id"):
        role_repo = RoleRepository(db, org_id)
        role = await role_repo.get(obj_in["role_id"])
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

    return await repo.create(obj_in)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> User:
    repo = UserRepository(db, org_id)
    user = await repo.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> User:
    repo = UserRepository(db, org_id)
    user = await repo.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    obj_in = data.model_dump(exclude_unset=True)
    password = obj_in.pop("password", None)
    if password:
        obj_in["password_hash"] = get_password_hash(password)

    if "role_id" in obj_in:
        role_repo = RoleRepository(db, org_id)
        role = await role_repo.get(obj_in["role_id"])
        if obj_in["role_id"] is not None and not role:
            raise HTTPException(status_code=404, detail="Role not found")

    return await repo.update(user, obj_in)


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> None:
    repo = UserRepository(db, org_id)
    user = await repo.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await repo.update(user, {"is_active": False})
