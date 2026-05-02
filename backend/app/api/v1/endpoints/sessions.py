import uuid
from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException, status
from redis.asyncio import Redis

from app.api.deps import get_current_user, require_role
from app.core.redis import get_redis_client
from app.models.user import User
from app.services.session_service import SessionService

router = APIRouter()


@router.get("/auth/sessions", response_model=List[dict])
async def list_my_sessions(
    current_user: User = Depends(get_current_user),
    redis_client: Redis = Depends(get_redis_client),
) -> List[dict]:
    service = SessionService(redis_client)
    return await service.list_sessions(str(current_user.id))


@router.delete("/auth/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def terminate_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    redis_client: Redis = Depends(get_redis_client),
):
    service = SessionService(redis_client)
    sessions = await service.list_sessions(str(current_user.id))
    if not any(s["session_id"] == session_id for s in sessions):
        raise HTTPException(status_code=404, detail="Session not found")
    await service.terminate_session(session_id)
    return None


@router.delete("/auth/sessions", status_code=status.HTTP_204_NO_CONTENT)
async def terminate_all_my_sessions(
    current_user: User = Depends(get_current_user),
    redis_client: Redis = Depends(get_redis_client),
):
    service = SessionService(redis_client)
    await service.terminate_all_sessions(str(current_user.id))
    return None


@router.delete(
    "/admin/users/{user_id}/sessions", status_code=status.HTTP_204_NO_CONTENT
)
async def admin_terminate_user_sessions(
    user_id: uuid.UUID,
    current_user: User = Depends(require_role(["Admin"])),
    redis_client: Redis = Depends(get_redis_client),
):
    service = SessionService(redis_client)
    await service.terminate_all_sessions(str(user_id))
    return None
