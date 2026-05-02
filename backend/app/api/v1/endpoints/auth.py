import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.redis import get_redis_client
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginResponse,
    RefreshTokenRequest,
    TokenResponse,
    TwoFADisableRequest,
    TwoFALoginVerifyRequest,
    TwoFASetupResponse,
    TwoFAVerifyRequest,
)
from app.schemas.user import UserLogin
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


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    data: UserLogin,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
    redis_client: Redis = Depends(get_redis_client),
) -> LoginResponse:
    rate_key = f"login_attempts:{org_id}:{data.email}"

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
            org_id=org_id,
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
