import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.redis import get_redis_client
from app.db.session import get_db
from app.schemas.search import SearchRequest, SearchResponse
from app.services.search_service import SearchService

router = APIRouter()
settings = get_settings()
DEFAULT_ORG_ID = settings.DEFAULT_ORG_ID if hasattr(settings, "DEFAULT_ORG_ID") else None


def get_org_id(
    x_org_id: str | None = Header(default=None, alias="X-Org-ID"),
) -> uuid.UUID:
    if x_org_id:
        return uuid.UUID(x_org_id)
    if DEFAULT_ORG_ID:
        return DEFAULT_ORG_ID
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.post("/", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_client),
    org_id: uuid.UUID = Depends(get_org_id),
) -> SearchResponse:
    service = SearchService(db, redis)
    try:
        return await service.search(request, org_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
