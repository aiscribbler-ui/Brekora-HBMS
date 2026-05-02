import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis_client
from app.core.security import get_password_hash
from app.db.session import get_db
from app.repositories.role import RoleRepository
from app.repositories.user import UserRepository
from app.schemas.auth import GoogleAuthRequest, GoogleAuthResponse
from app.schemas.user import UserRead
from app.services.auth_service import AuthService
from app.services.google_oauth_service import GoogleOAuthService

router = APIRouter()
DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.post("/auth/google", response_model=GoogleAuthResponse)
async def google_login(
    request: Request,
    data: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
) -> GoogleAuthResponse:
    try:
        payload = GoogleOAuthService.verify_token(data.id_token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )

    email = payload.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not found in Google token",
        )

    name = payload.get("name", "")
    picture = payload.get("picture", "")
    google_id = payload.get("sub")

    repo = UserRepository(db, DEFAULT_ORG_ID)
    user = await repo.get_by_email(email)

    if user:
        if not user.google_id:
            await repo.update(user, {"google_id": google_id})
    else:
        role_repo = RoleRepository(db, DEFAULT_ORG_ID)
        guest_role = await role_repo.get_by_name("Guest")
        user = await repo.create(
            {
                "email": email,
                "password_hash": get_password_hash(secrets.token_urlsafe(32)),
                "first_name": name,
                "last_name": None,
                "role_id": guest_role.id if guest_role else None,
                "is_active": True,
            }
        )
        await repo.update(user, {"google_id": google_id})

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive",
        )

    auth_service = AuthService(db, redis_client)
    tokens = await auth_service._issue_tokens_and_session(
        user,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": tokens["token_type"],
        "expires_in": tokens["expires_in"],
        "session_id": tokens["session_id"],
        "user": UserRead.model_validate(user),
    }
