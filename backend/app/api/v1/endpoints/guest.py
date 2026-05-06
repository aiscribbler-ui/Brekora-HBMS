import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import get_password_hash
from app.db.session import get_db
from app.models.user import User
from app.repositories.booking import BookingRepository
from app.repositories.user import UserRepository
from app.schemas.booking import BookingRead
from app.schemas.user import UserRead, UserUpdate

router = APIRouter()


@router.get("/me", response_model=UserRead)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserRead:
    return UserRead.model_validate(current_user)


@router.patch("/me", response_model=UserRead)
async def update_me(
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserRead:
    repo = UserRepository(db, current_user.org_id)
    obj_in = data.model_dump(exclude_unset=True)
    password = obj_in.pop("password", None)
    if password:
        obj_in["password_hash"] = get_password_hash(password)
    if "role_id" in obj_in:
        obj_in.pop("role_id")
    if "email" in obj_in:
        obj_in.pop("email")
    if "is_active" in obj_in:
        obj_in.pop("is_active")
    updated = await repo.update(current_user, obj_in)
    return UserRead.model_validate(updated)


@router.get("/bookings", response_model=List[BookingRead])
async def get_my_bookings(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[BookingRead]:
    if not current_user.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    repo = BookingRepository(db, current_user.org_id)
    bookings = await repo.get_by_guest(current_user.id, skip=skip, limit=limit)
    return bookings
