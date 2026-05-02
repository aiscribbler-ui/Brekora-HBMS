import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.repositories.system_config import SystemConfigRepository
from app.schemas.gst import GSTRateRead
from app.services.gst_service import GSTService
from app.api.deps import get_current_user, require_role

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


class GSTRateUpdate(BaseModel):
    value: str


class SplitUpdate(BaseModel):
    owner_percentage: str
    brekora_percentage: str


@router.get("/rate", response_model=GSTRateRead)
async def get_gst_rate(
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
    current_user=Depends(get_current_user),
) -> GSTRateRead:
    repo = SystemConfigRepository(db, org_id)
    config = await repo.get_by_key("gst_rate")
    if config is None:
        raise HTTPException(status_code=404, detail="GST rate not configured")
    return GSTRateRead(key=config.key, value=config.value, data_type=config.data_type)


@router.patch("/rate", response_model=GSTRateRead)
async def update_gst_rate(
    data: GSTRateUpdate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
    current_user=Depends(require_role(["Admin", "Manager"])),
) -> GSTRateRead:
    # Validate decimal
    try:
        Decimal(data.value)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid decimal value for GST rate")

    repo = SystemConfigRepository(db, org_id)
    config = await repo.get_by_key("gst_rate")
    if config is None:
        config = await repo.create({"key": "gst_rate", "value": data.value, "data_type": "number"})
    else:
        config = await repo.update(config, {"value": data.value})
    return GSTRateRead(key=config.key, value=config.value, data_type=config.data_type)


@router.get("/split")
async def get_default_split(
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
    current_user=Depends(get_current_user),
):
    repo = SystemConfigRepository(db, org_id)
    owner_config = await repo.get_by_key("default_owner_split")
    brekora_config = await repo.get_by_key("default_brekora_split")
    return {
        "default_owner_split": owner_config.value if owner_config else "70.00",
        "default_brekora_split": brekora_config.value if brekora_config else "30.00",
    }


@router.patch("/split")
async def update_default_split(
    data: SplitUpdate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
    current_user=Depends(require_role(["Admin"])),
):
    try:
        owner_pct = Decimal(data.owner_percentage)
        brekora_pct = Decimal(data.brekora_percentage)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid decimal values for split percentages")

    if owner_pct + brekora_pct != Decimal("100.00"):
        raise HTTPException(status_code=422, detail="Split percentages must sum to 100")

    repo = SystemConfigRepository(db, org_id)

    owner_config = await repo.get_by_key("default_owner_split")
    if owner_config is None:
        owner_config = await repo.create({
            "key": "default_owner_split",
            "value": str(owner_pct.quantize(Decimal("0.01"))),
            "data_type": "number",
        })
    else:
        owner_config = await repo.update(owner_config, {"value": str(owner_pct.quantize(Decimal("0.01")))})

    brekora_config = await repo.get_by_key("default_brekora_split")
    if brekora_config is None:
        brekora_config = await repo.create({
            "key": "default_brekora_split",
            "value": str(brekora_pct.quantize(Decimal("0.01"))),
            "data_type": "number",
        })
    else:
        brekora_config = await repo.update(brekora_config, {"value": str(brekora_pct.quantize(Decimal("0.01")))})

    return {
        "default_owner_split": owner_config.value,
        "default_brekora_split": brekora_config.value,
    }
