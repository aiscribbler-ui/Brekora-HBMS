import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.api.deps import get_current_user
from app.services.owner_service import OwnerService

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


def _parse_month(month_str: str) -> date:
    try:
        year, mon = month_str.split("-")
        return date(int(year), int(mon), 1)
    except Exception:
        raise HTTPException(status_code=422, detail="month must be YYYY-MM")


@router.get("/pnl")
async def get_owner_pnl(
    property_id: uuid.UUID = Query(...),
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
    current_user=Depends(get_current_user),
):
    svc = OwnerService(db, org_id)
    result = await svc.calculate_pnl(property_id, _parse_month(month))
    return result


@router.get("/payout")
async def get_owner_payout(
    property_id: uuid.UUID = Query(...),
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
    current_user=Depends(get_current_user),
):
    svc = OwnerService(db, org_id)
    payout = await svc.calculate_payout(property_id, _parse_month(month))
    return {
        "id": str(payout.id),
        "property_id": str(payout.property_id),
        "month": payout.month,
        "gross_amount": float(payout.gross_amount),
        "ota_commission": float(payout.ota_commission),
        "partner_commission": float(payout.partner_commission),
        "gst_amount": float(payout.gst_amount),
        "net_distributable": float(payout.net_distributable),
        "owner_share": float(payout.owner_share),
        "brekora_share": float(payout.brekora_share),
        "owner_percentage": float(payout.owner_percentage),
        "brekora_percentage": float(payout.brekora_percentage),
        "status": payout.status,
        "created_at": payout.created_at.isoformat() if payout.created_at else None,
        "updated_at": payout.updated_at.isoformat() if payout.updated_at else None,
    }


@router.get("/statement")
async def get_owner_statement(
    property_id: uuid.UUID = Query(...),
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
    current_user=Depends(get_current_user),
):
    svc = OwnerService(db, org_id)
    result = await svc.generate_monthly_statement(property_id, _parse_month(month))
    return result
