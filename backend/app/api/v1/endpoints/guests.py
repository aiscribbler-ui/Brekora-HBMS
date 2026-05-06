import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.redis import get_redis_client
from app.core.security import get_password_hash, verify_password
from app.db.session import get_db
from app.models.booking import Booking
from app.models.user import User
from app.repositories.role import RoleRepository
from app.repositories.user import UserRepository
from app.schemas.auth import LoginResponse
from app.services.auth_service import AuthService

router = APIRouter()
DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def get_org_id(x_org_id: str | None = Header(default=None, alias="X-Org-ID")) -> uuid.UUID:
    if x_org_id:
        return uuid.UUID(x_org_id)
    return DEFAULT_ORG_ID


class GuestSignupRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str | None = None
    password: str


class GuestProfile(BaseModel):
    id: uuid.UUID
    first_name: str | None = None
    last_name: str | None = None
    email: str
    phone: str | None = None


class GuestProfileUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    current_password: str | None = None
    new_password: str | None = None


class GuestBookingRead(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID
    check_in: datetime
    check_out: datetime
    status: str
    total_amount: float
    currency: str


def _to_profile(user: User) -> GuestProfile:
    return GuestProfile(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        phone=user.phone,
    )


@router.post("/guest/signup", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def guest_signup(
    request: Request,
    data: GuestSignupRequest,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
    redis_client: Redis = Depends(get_redis_client),
) -> LoginResponse:
    user_repo = UserRepository(db, org_id)
    existing = await user_repo.get_by_email(data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    role_repo = RoleRepository(db, org_id)
    guest_role = await role_repo.get_by_name("Guest")

    user = await user_repo.create(
        {
            "email": data.email,
            "phone": data.phone,
            "password_hash": get_password_hash(data.password),
            "first_name": data.first_name,
            "last_name": data.last_name,
            "role_id": guest_role.id if guest_role else None,
            "is_active": True,
        }
    )
    await db.flush()

    auth_service = AuthService(db, redis_client)
    tokens = await auth_service._issue_tokens_and_session(
        user,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return LoginResponse(**tokens)


@router.get("/guest/me", response_model=GuestProfile)
async def get_guest_me(current_user: User = Depends(get_current_user)) -> GuestProfile:
    return _to_profile(current_user)


@router.patch("/guest/me", response_model=GuestProfile)
async def update_guest_me(
    data: GuestProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GuestProfile:
    updates: dict = {}
    if data.first_name is not None:
        updates["first_name"] = data.first_name
    if data.last_name is not None:
        updates["last_name"] = data.last_name
    if data.phone is not None:
        updates["phone"] = data.phone

    if data.new_password:
        if not data.current_password or not verify_password(
            data.current_password, current_user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect.",
            )
        updates["password_hash"] = get_password_hash(data.new_password)

    if not updates:
        return _to_profile(current_user)

    repo = UserRepository(db, current_user.org_id)
    user = await repo.update(current_user, updates)
    return _to_profile(user)


@router.get("/guest/bookings", response_model=List[GuestBookingRead])
async def list_guest_bookings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[GuestBookingRead]:
    stmt = (
        select(Booking)
        .where(Booking.guest_id == current_user.id)
        .order_by(Booking.check_in.desc())
    )
    result = await db.execute(stmt)
    bookings = result.scalars().all()
    return [
        GuestBookingRead(
            id=b.id,
            property_id=b.property_id,
            check_in=datetime.combine(b.check_in, datetime.min.time()),
            check_out=datetime.combine(b.check_out, datetime.min.time()),
            status=b.status,
            total_amount=float(b.total_amount or 0),
            currency=b.currency or "INR",
        )
        for b in bookings
    ]
