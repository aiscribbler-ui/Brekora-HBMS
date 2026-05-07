import uuid
from datetime import date, time

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_current_user_with_properties,
    UserWithProperties,
    _ORG_LEVEL_PROPERTY_ACCESS_ROLES,
)
from app.core.config import get_settings
from app.core.redis import get_redis_client
from app.db.session import get_db
from app.schemas.availability import (
    AddOnAvailabilitySlot,
    RoomAvailabilityNight,
)
from app.services.availability_service import AvailabilityService

router = APIRouter()
settings = get_settings()
DEFAULT_ORG_ID = settings.DEFAULT_ORG_ID if hasattr(settings, "DEFAULT_ORG_ID") else None


def get_org_id(x_org_id: str | None = Header(default=None, alias="X-Org-ID")) -> uuid.UUID:
    if x_org_id:
        return uuid.UUID(x_org_id)
    if DEFAULT_ORG_ID:
        return DEFAULT_ORG_ID
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.get("/rooms", response_model=list[RoomAvailabilityNight])
async def get_room_availability(
    property_id: uuid.UUID = Query(...),
    room_type_id: uuid.UUID | None = Query(default=None),
    check_in: date = Query(...),
    check_out: date = Query(...),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_client),
    org_id: uuid.UUID = Depends(get_org_id),
    current: UserWithProperties = Depends(get_current_user_with_properties),
) -> list[RoomAvailabilityNight]:
    global_role = current.user.role.name if current.user.role else None
    if global_role not in _ORG_LEVEL_PROPERTY_ACCESS_ROLES:
        if property_id not in current.property_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this property",
            )

    if check_in >= check_out:
        raise HTTPException(
            status_code=422,
            detail="check_out must be after check_in",
        )

    svc = AvailabilityService(db, redis)
    rows = await svc.get_room_availability(
        property_id=property_id,
        room_type_id=room_type_id,
        check_in=check_in,
        check_out=check_out,
        org_id=org_id,
    )

    return [RoomAvailabilityNight(**row) for row in rows]


@router.get("/addons", response_model=list[AddOnAvailabilitySlot])
async def get_addon_availability(
    add_on_id: uuid.UUID = Query(...),
    date: date = Query(...),
    slot_time: time | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_client),
) -> list[AddOnAvailabilitySlot]:
    svc = AvailabilityService(db, redis)
    rows = await svc.get_addon_availability(
        add_on_id=add_on_id,
        query_date=date,
        slot_time=slot_time,
    )
    return [AddOnAvailabilitySlot(**row) for row in rows]


@router.get("/addons/range", response_model=list[AddOnAvailabilitySlot])
async def get_addon_availability_range(
    add_on_id: uuid.UUID = Query(...),
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_client),
) -> list[AddOnAvailabilitySlot]:
    if start_date > end_date:
        raise HTTPException(
            status_code=422,
            detail="end_date must be after start_date",
        )

    svc = AvailabilityService(db, redis)
    rows = await svc.get_addon_availability_range(
        add_on_id=add_on_id,
        start_date=start_date,
        end_date=end_date,
    )
    return [AddOnAvailabilitySlot(**row) for row in rows]
