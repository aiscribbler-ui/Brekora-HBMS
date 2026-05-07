import uuid
from dataclasses import dataclass
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
from app.repositories.user_property import UserPropertyRepository
from app.services.session_service import SessionService

security = HTTPBearer(auto_error=False)


@dataclass
class UserWithProperties:
    user: User
    property_ids: list[uuid.UUID]
    property_roles: dict[uuid.UUID, str]


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


async def get_current_user_with_properties(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserWithProperties:
    repo = UserPropertyRepository(db)
    rows = await repo.get_by_user(current_user.id)
    property_ids = [r.property_id for r in rows]
    property_roles = {r.property_id: r.role_at_property for r in rows}
    return UserWithProperties(
        user=current_user,
        property_ids=property_ids,
        property_roles=property_roles,
    )


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


# Global roles that bypass property-level access checks
_ORG_LEVEL_PROPERTY_ACCESS_ROLES = ("Admin", "Owner", "Manager")


def require_property_role(required_role: str):
    async def property_role_checker(
        current: UserWithProperties = Depends(get_current_user_with_properties),
    ) -> UserWithProperties:
        global_role = current.user.role.name if current.user.role else None
        if global_role in _ORG_LEVEL_PROPERTY_ACCESS_ROLES:
            return current

        if not current.property_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No property access",
            )

        if required_role not in current.property_roles.values():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient property-level permissions",
            )
        return current

    return property_role_checker
