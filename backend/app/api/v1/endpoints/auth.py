import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.redis import get_redis_client
from app.core.security import create_access_token, create_refresh_token, get_password_hash
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginResponse,
    MeResponse,
    RefreshTokenRequest,
    SetupRequest,
    SetupStatusResponse,
    TokenResponse,
    TwoFADisableRequest,
    TwoFALoginVerifyRequest,
    TwoFASetupResponse,
    TwoFAVerifyRequest,
)
from app.schemas.user import UserCreate, UserLogin
from app.services.auth_service import AuthService
from app.services.totp_service import TOTPService

router = APIRouter()
DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def get_org_id(x_org_id: str | None = Header(default=None, alias="X-Org-ID")) -> uuid.UUID:
    if x_org_id:
        return uuid.UUID(x_org_id)
    return DEFAULT_ORG_ID


async def _check_rate_limit(
    redis_client: Redis, key: str, max_attempts: int = 5, window_seconds: int = 900
) -> bool:
    current = await redis_client.get(key)
    if current and int(current) >= max_attempts:
        return False
    pipe = redis_client.pipeline()
    pipe.incr(key)
    pipe.expire(key, window_seconds)
    await pipe.execute()
    return True


@router.get("/me", response_model=MeResponse)
async def me(current_user: User = Depends(get_current_user)) -> MeResponse:
    role_name = current_user.role.name if current_user.role else None
    full_name = f"{current_user.first_name or ''} {current_user.last_name or ''}".strip() or None
    return MeResponse(
        id=current_user.id,
        org_id=current_user.org_id,
        email=current_user.email,
        role=role_name,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        name=full_name,
        is_2fa_enabled=bool(current_user.is_2fa_enabled),
        is_active=bool(current_user.is_active),
        last_login=current_user.last_login,
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    data: UserLogin,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
    redis_client: Redis = Depends(get_redis_client),
) -> LoginResponse:
    from app.repositories.user import UserRepository

    # If no X-Org-ID header was provided, look up user globally to discover their org
    effective_org_id = org_id
    header_org_id = request.headers.get("x-org-id")
    if not header_org_id:
        user_repo = UserRepository(db, org_id)
        user = await user_repo.get_by_email_unscoped(data.email)
        if user:
            effective_org_id = user.org_id

    rate_key = f"login_attempts:{effective_org_id}:{data.email}"

    allowed = await _check_rate_limit(redis_client, rate_key)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again in 15 minutes.",
        )

    auth_service = AuthService(db, redis_client)
    try:
        result = await auth_service.login(
            email=data.email,
            password=data.password,
            org_id=effective_org_id,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        )

    await redis_client.delete(rate_key)
    return result


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    data: RefreshTokenRequest,
    redis_client: Redis = Depends(get_redis_client),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    auth_service = AuthService(db, redis_client)
    try:
        result = await auth_service.refresh(data.refresh_token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        )
    return result


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    data: RefreshTokenRequest,
    redis_client: Redis = Depends(get_redis_client),
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
) -> None:
    auth_service = AuthService(None, redis_client)
    await auth_service.logout(data.refresh_token, x_session_id)
    return None


@router.post("/2fa/setup", response_model=TwoFASetupResponse)
async def setup_2fa(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TwoFASetupResponse:
    secret = TOTPService.generate_secret()
    from app.repositories.user import UserRepository
    repo = UserRepository(db, current_user.org_id)
    await repo.update(current_user, {"totp_secret": secret})
    provisioning_uri = TOTPService.get_provisioning_uri(current_user.email, secret)
    return {"secret": secret, "provisioning_uri": provisioning_uri}


@router.post("/2fa/verify", status_code=status.HTTP_204_NO_CONTENT)
async def verify_2fa(
    data: TwoFAVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA not set up",
        )
    if not TOTPService.verify_token(data.secret, data.token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid TOTP token",
        )
    from app.repositories.user import UserRepository
    repo = UserRepository(db, current_user.org_id)
    await repo.update(current_user, {"is_2fa_enabled": True, "totp_secret": data.secret})
    return None


@router.post("/2fa/disable", status_code=status.HTTP_204_NO_CONTENT)
async def disable_2fa(
    data: TwoFADisableRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    if not current_user.totp_secret or not current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled",
        )
    if not TOTPService.verify_token(current_user.totp_secret, data.token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid TOTP token",
        )
    from app.repositories.user import UserRepository
    repo = UserRepository(db, current_user.org_id)
    await repo.update(current_user, {"is_2fa_enabled": False, "totp_secret": None})
    return None


@router.post("/2fa/login-verify", response_model=TokenResponse)
async def login_verify_2fa(
    request: Request,
    data: TwoFALoginVerifyRequest,
    redis_client: Redis = Depends(get_redis_client),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    auth_service = AuthService(db, redis_client)
    try:
        result = await auth_service.login_verify_2fa(
            temp_token=data.temp_token,
            token=data.token,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        )
    return result


@router.get("/setup-status", response_model=SetupStatusResponse)
async def setup_status(db: AsyncSession = Depends(get_db)) -> SetupStatusResponse:
    from sqlalchemy import func, select
    from app.models.user import User

    count_result = await db.execute(select(func.count()).select_from(User))
    user_count = count_result.scalar() or 0
    return SetupStatusResponse(setup_required=user_count == 0)


@router.post("/setup", status_code=status.HTTP_201_CREATED)
async def setup(
    request: Request,
    data: SetupRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
) -> dict:
    from sqlalchemy import func, select

    from app.models.organization import Organization
    from app.models.role import Role
    from app.models.user import User
    from app.services.session_service import SessionService

    # Guard: only allow when no users exist
    count_result = await db.execute(select(func.count()).select_from(User))
    user_count = count_result.scalar() or 0
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Setup already completed.",
        )

    # Remove any pre-seeded default organizations/roles from migrations
    # so the new admin gets a clean org with their chosen slug.
    existing_orgs = await db.execute(select(Organization))
    for org_obj in existing_orgs.scalars().all():
        await db.delete(org_obj)
    await db.flush()

    # 1. Create default organization
    org_slug = data.org_name.lower().strip().replace(" ", "-")[:50]
    org = Organization(name=data.org_name, slug=org_slug)
    db.add(org)
    await db.flush()
    await db.refresh(org)

    # 2. Create Admin role for this org
    admin_role = Role(org_id=org.id, name="Admin", description="System administrator with full access")
    db.add(admin_role)
    await db.flush()
    await db.refresh(admin_role)

    # 3. Create ListingManager role for this org
    listing_role = Role(
        org_id=org.id,
        name="ListingManager",
        description="Manages OTA listings and content across all properties",
    )
    db.add(listing_role)
    await db.flush()
    await db.refresh(listing_role)

    # 4. Create Owner role
    owner_role = Role(org_id=org.id, name="Owner", description="Property owner")
    db.add(owner_role)
    await db.flush()
    await db.refresh(owner_role)

    # 5. Create Manager role
    manager_role = Role(org_id=org.id, name="Manager", description="Property manager")
    db.add(manager_role)
    await db.flush()
    await db.refresh(manager_role)

    # 6. Create Partner role
    partner_role = Role(org_id=org.id, name="Partner", description="Business partner")
    db.add(partner_role)
    await db.flush()
    await db.refresh(partner_role)

    # 7. Create Guest role
    guest_role = Role(org_id=org.id, name="Guest", description="Direct booking guest")
    db.add(guest_role)
    await db.flush()
    await db.refresh(guest_role)

    # 8. Create first admin user
    password_hash = get_password_hash(data.admin_password)
    first_name = (data.admin_name or "").strip().split(" ")[0] if data.admin_name else None
    last_name = " ".join((data.admin_name or "").strip().split(" ")[1:]) if data.admin_name else None
    admin_user = User(
        org_id=org.id,
        email=data.admin_email.lower().strip(),
        password_hash=password_hash,
        first_name=first_name,
        last_name=last_name,
        role_id=admin_role.id,
        is_active=True,
        is_2fa_enabled=False,
    )
    db.add(admin_user)
    await db.flush()
    await db.refresh(admin_user)

    # 8. Issue tokens and session
    role_name = admin_role.name
    name = f"{first_name or ''} {last_name or ''}".strip()
    access_token = create_access_token(
        admin_user.id, org.id, role=role_name, email=admin_user.email, name=name or None
    )
    refresh_jti = uuid.uuid4()
    refresh_token = create_refresh_token(admin_user.id, org.id, refresh_jti)

    settings = get_settings()
    ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    await redis_client.setex(f"refresh:{refresh_jti}", ttl, str(admin_user.id))

    session_service = SessionService(redis_client)
    session_id = await session_service.create_session(
        user_id=str(admin_user.id),
        role=role_name,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    await db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "session_id": session_id,
    }


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, uuid.UUID | str]:
    from app.repositories.role import RoleRepository
    from app.repositories.user import UserRepository

    user_repo = UserRepository(db, DEFAULT_ORG_ID)
    existing = await user_repo.get_by_email(str(data.email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    role_repo = RoleRepository(db, DEFAULT_ORG_ID)
    guest_role = await role_repo.get_by_name("Guest")
    if not guest_role:
        guest_role = await role_repo.create(
            {"name": "Guest", "description": "Default guest role"}
        )

    password_hash = get_password_hash(data.password)
    user = await user_repo.create(
        {
            "email": data.email,
            "password_hash": password_hash,
            "first_name": data.first_name,
            "last_name": data.last_name,
            "phone": data.phone,
            "role_id": guest_role.id,
            "is_active": True,
        }
    )

    return {"id": user.id, "email": user.email}
