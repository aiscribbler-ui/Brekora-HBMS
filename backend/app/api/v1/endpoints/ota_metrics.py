from datetime import date
from typing import Any, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.parse_metric import ParseMetricRead
from app.services.parse_metric_service import ParseMetricService

router = APIRouter()
settings = get_settings()


@router.get("/", response_model=List[ParseMetricRead])
async def list_ota_metrics(
    start: date = Query(..., description="Start date (inclusive)"),
    end: date = Query(..., description="End date (inclusive)"),
    ota_source: str | None = Query(default=None, description="Filter by OTA source"),
    db: AsyncSession = Depends(get_db),
    _user: Any = Depends(require_role(["Admin"])),
) -> List[ParseMetricRead]:
    svc = ParseMetricService(db)
    return await svc.get_metrics(start, end, ota_source)


@router.get("/accuracy")
async def get_ota_accuracy(
    ota_source: str = Query(..., description="OTA source to calculate accuracy for"),
    days: int = Query(default=30, ge=1, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db),
    _user: Any = Depends(require_role(["Admin"])),
) -> dict[str, Any]:
    svc = ParseMetricService(db)
    accuracy = await svc.get_accuracy(ota_source, days)
    return {"ota_source": ota_source, "days": days, "accuracy": accuracy}
