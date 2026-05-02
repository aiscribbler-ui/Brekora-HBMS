"""API endpoints for failed parse alerts."""
import uuid
from typing import Any, List

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.parsed_booking_queue import ParsedBookingQueueRead
from app.services.parse_alert_service import ParseAlertService

router = APIRouter()
settings = get_settings()
DEFAULT_ORG_ID = settings.DEFAULT_ORG_ID


def get_org_id(
    x_org_id: str | None = Header(default=None, alias="X-Org-ID"),
) -> uuid.UUID:
    if x_org_id:
        return uuid.UUID(x_org_id)
    return DEFAULT_ORG_ID


@router.get("/", response_model=List[ParsedBookingQueueRead])
async def list_failed_parses(
    source_type: str | None = Query(default=None),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> List[Any]:
    """List failed parse alerts with optional source filter and pagination."""
    svc = ParseAlertService(db, org_id)
    return await svc.list_failed(source_type=source_type, skip=skip, limit=limit)


@router.get("/count")
async def count_failed_parses(
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> Any:
    """Return count of failed parses per OTA source."""
    svc = ParseAlertService(db, org_id)
    return await svc.count_by_source()


@router.post("/{alert_id}/retry", response_model=ParsedBookingQueueRead)
async def retry_failed_parse(
    alert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> Any:
    """Retry parsing the raw email linked to a failed alert."""
    svc = ParseAlertService(db, org_id)
    try:
        updated = await svc.retry(alert_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return updated
