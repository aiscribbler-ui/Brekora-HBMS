import uuid
from typing import List

from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis_client
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.repositories.user import UserRepository
from app.services.session_service import SessionService

security = HTTPBearer(auto_error=False)


async def get_current_session(
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
    redis_client: Redis = Depends(get_redis_client),
) -> str | None:
    if not x_session_id:
        return None
    session_service = SessionService(redis_client)
    if not await session_service.validate_session(x_session_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return x_session_id


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
    session_id: str | None = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    org_id = payload.get("org_id")
    if not user_id or not org_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    repo = UserRepository(db, uuid.UUID(org_id))
    user = await repo.get(uuid.UUID(user_id))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if session_id:
        session_service = SessionService(redis_client)
        session_data = await session_service.get_session(session_id)
        if not session_data or session_data.get("user_id") != str(user.id):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session mismatch",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return user


def require_role(allowed_roles: List[str]):
    async def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if not current_user.role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User has no assigned role",
            )
        if current_user.role.name not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return role_checker
