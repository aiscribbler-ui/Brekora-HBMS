import uuid
from datetime import date
from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.models.rate_plan import RatePlan
from app.models.seasonal_calendar import SeasonalCalendar
from app.models.promo_code import PromoCode
from app.repositories.pricing import RatePlanRepository, SeasonalCalendarRepository, PromoCodeRepository
from app.schemas.pricing import (
    PriceBreakdown,
    RatePlanCreate,
    RatePlanRead,
    RatePlanUpdate,
    SeasonalCalendarCreate,
    SeasonalCalendarRead,
    SeasonalCalendarUpdate,
    PromoCodeCreate,
    PromoCodeRead,
    PromoCodeUpdate,
)
from app.services.pricing_service import PricingService

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


# ---------------------------------------------------------------------------
# Pricing calculation endpoints
# ---------------------------------------------------------------------------

@router.get("/calculate-room", response_model=PriceBreakdown)
async def calculate_room_price(
    room_type_id: uuid.UUID,
    check_in: date,
    check_out: date,
    rate_plan_code: str | None = Query(default=None),
    guests: int | None = Query(default=None),
    promo_code: str | None = Query(default=None),
    channel_source: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> PriceBreakdown:
    service = PricingService(db)
    return await service.calculate_room_price(
        room_type_id=room_type_id,
        check_in=check_in,
        check_out=check_out,
        rate_plan_code=rate_plan_code,
        guests=guests,
        promo_code=promo_code,
        channel_source=channel_source,
    )


@router.get("/calculate-package", response_model=PriceBreakdown)
async def calculate_package_price(
    package_id: uuid.UUID,
    check_in: date,
    check_out: date,
    guests: int | None = Query(default=None),
    promo_code: str | None = Query(default=None),
    channel_source: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> PriceBreakdown:
    service = PricingService(db)
    return await service.calculate_package_price(
        package_id=package_id,
        check_in=check_in,
        check_out=check_out,
        guests=guests,
        promo_code=promo_code,
        channel_source=channel_source,
    )


# ---------------------------------------------------------------------------
# Rate Plan CRUD
# ---------------------------------------------------------------------------

@router.get("/rate-plans", response_model=List[RatePlanRead])
async def list_rate_plans(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> List[RatePlan]:
    repo = RatePlanRepository(db, org_id)
    return await repo.get_multi(skip=skip, limit=limit)


@router.post("/rate-plans", response_model=RatePlanRead, status_code=201)
async def create_rate_plan(
    data: RatePlanCreate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> RatePlan:
    repo = RatePlanRepository(db, org_id)
    obj_in = data.model_dump(exclude_unset=True)
    if "org_id" in obj_in and obj_in["org_id"] is None:
        del obj_in["org_id"]
    return await repo.create(obj_in)


@router.get("/rate-plans/{rate_plan_id}", response_model=RatePlanRead)
async def get_rate_plan(
    rate_plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> RatePlan:
    repo = RatePlanRepository(db, org_id)
    rp = await repo.get(rate_plan_id)
    if not rp:
        raise HTTPException(status_code=404, detail="Rate plan not found")
    return rp


@router.patch("/rate-plans/{rate_plan_id}", response_model=RatePlanRead)
async def update_rate_plan(
    rate_plan_id: uuid.UUID,
    data: RatePlanUpdate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> RatePlan:
    repo = RatePlanRepository(db, org_id)
    rp = await repo.get(rate_plan_id)
    if not rp:
        raise HTTPException(status_code=404, detail="Rate plan not found")
    update_data = data.model_dump(exclude_unset=True)
    return await repo.update(rp, update_data)


@router.delete("/rate-plans/{rate_plan_id}", status_code=204)
async def delete_rate_plan(
    rate_plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> None:
    repo = RatePlanRepository(db, org_id)
    rp = await repo.get(rate_plan_id)
    if not rp:
        raise HTTPException(status_code=404, detail="Rate plan not found")
    await repo.update(rp, {"is_active": False})


# ---------------------------------------------------------------------------
# Seasonal Calendar CRUD
# ---------------------------------------------------------------------------

@router.get("/seasonal-calendars", response_model=List[SeasonalCalendarRead])
async def list_seasonal_calendars(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> List[SeasonalCalendar]:
    repo = SeasonalCalendarRepository(db, org_id)
    return await repo.get_multi(skip=skip, limit=limit)


@router.post("/seasonal-calendars", response_model=SeasonalCalendarRead, status_code=201)
async def create_seasonal_calendar(
    data: SeasonalCalendarCreate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> SeasonalCalendar:
    repo = SeasonalCalendarRepository(db, org_id)
    obj_in = data.model_dump(exclude_unset=True)
    if "org_id" in obj_in and obj_in["org_id"] is None:
        del obj_in["org_id"]
    return await repo.create(obj_in)


@router.get("/seasonal-calendars/{seasonal_calendar_id}", response_model=SeasonalCalendarRead)
async def get_seasonal_calendar(
    seasonal_calendar_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> SeasonalCalendar:
    repo = SeasonalCalendarRepository(db, org_id)
    sc = await repo.get(seasonal_calendar_id)
    if not sc:
        raise HTTPException(status_code=404, detail="Seasonal calendar not found")
    return sc


@router.patch("/seasonal-calendars/{seasonal_calendar_id}", response_model=SeasonalCalendarRead)
async def update_seasonal_calendar(
    seasonal_calendar_id: uuid.UUID,
    data: SeasonalCalendarUpdate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> SeasonalCalendar:
    repo = SeasonalCalendarRepository(db, org_id)
    sc = await repo.get(seasonal_calendar_id)
    if not sc:
        raise HTTPException(status_code=404, detail="Seasonal calendar not found")
    update_data = data.model_dump(exclude_unset=True)
    return await repo.update(sc, update_data)


@router.delete("/seasonal-calendars/{seasonal_calendar_id}", status_code=204)
async def delete_seasonal_calendar(
    seasonal_calendar_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> None:
    repo = SeasonalCalendarRepository(db, org_id)
    sc = await repo.get(seasonal_calendar_id)
    if not sc:
        raise HTTPException(status_code=404, detail="Seasonal calendar not found")
    await repo.update(sc, {"is_active": False})


# ---------------------------------------------------------------------------
# Promo Code CRUD
# ---------------------------------------------------------------------------

@router.get("/promo-codes", response_model=List[PromoCodeRead])
async def list_promo_codes(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> List[PromoCode]:
    repo = PromoCodeRepository(db, org_id)
    return await repo.get_multi(skip=skip, limit=limit)


@router.post("/promo-codes", response_model=PromoCodeRead, status_code=201)
async def create_promo_code(
    data: PromoCodeCreate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> PromoCode:
    repo = PromoCodeRepository(db, org_id)
    obj_in = data.model_dump(exclude_unset=True)
    if "org_id" in obj_in and obj_in["org_id"] is None:
        del obj_in["org_id"]
    return await repo.create(obj_in)


@router.get("/promo-codes/{promo_code_id}", response_model=PromoCodeRead)
async def get_promo_code(
    promo_code_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> PromoCode:
    repo = PromoCodeRepository(db, org_id)
    pc = await repo.get(promo_code_id)
    if not pc:
        raise HTTPException(status_code=404, detail="Promo code not found")
    return pc


@router.patch("/promo-codes/{promo_code_id}", response_model=PromoCodeRead)
async def update_promo_code(
    promo_code_id: uuid.UUID,
    data: PromoCodeUpdate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> PromoCode:
    repo = PromoCodeRepository(db, org_id)
    pc = await repo.get(promo_code_id)
    if not pc:
        raise HTTPException(status_code=404, detail="Promo code not found")
    update_data = data.model_dump(exclude_unset=True)
    return await repo.update(pc, update_data)


@router.delete("/promo-codes/{promo_code_id}", status_code=204)
async def delete_promo_code(
    promo_code_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> None:
    repo = PromoCodeRepository(db, org_id)
    pc = await repo.get(promo_code_id)
    if not pc:
        raise HTTPException(status_code=404, detail="Promo code not found")
    await repo.update(pc, {"is_active": False})
