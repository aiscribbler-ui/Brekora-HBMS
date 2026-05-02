import uuid
from datetime import date
from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.redis import get_redis_client
from app.db.session import get_db
from app.models.booking import BookingStatus
from app.repositories.booking import BookingRepository
from app.repositories.property import PropertyRepository
from app.repositories.user import UserRepository
from app.schemas.booking import (
    BookingCreate,
    BookingInitRequest,
    BookingInitResponse,
    BookingModificationRequest,
    BookingModificationResponse,
    BookingRead,
    BookingUpdate,
)
from app.exceptions import BookingConflictError
from app.schemas.conflict import BookingConflictResponse
from app.services.booking_service import BookingInitService
from app.services.booking_modification_service import BookingModificationService

router = APIRouter()

settings = get_settings()
DEFAULT_ORG_ID = settings.DEFAULT_ORG_ID


def get_org_id(
    x_org_id: str | None = Header(default=None, alias="X-Org-ID"),
) -> uuid.UUID:
    if x_org_id:
        return uuid.UUID(x_org_id)
    return DEFAULT_ORG_ID


VALID_STATUS_TRANSITIONS: dict[str, set[str]] = {
    BookingStatus.pending_payment.value: {
        BookingStatus.confirmed.value,
        BookingStatus.payment_failed.value,
        BookingStatus.cancelled.value,
    },
    BookingStatus.confirmed.value: {
        BookingStatus.cancelled.value,
        BookingStatus.completed.value,
    },
    BookingStatus.payment_failed.value: {
        BookingStatus.pending_payment.value,
        BookingStatus.cancelled.value,
    },
    BookingStatus.cancelled.value: set(),
    BookingStatus.completed.value: set(),
}


def _validate_status_transition(current: str | None, new: str) -> None:
    if current is None:
        return
    allowed = VALID_STATUS_TRANSITIONS.get(current, set())
    if new not in allowed and new != current:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from {current} to {new}",
        )


@router.get("/", response_model=List[BookingRead])
async def list_bookings(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> List[BookingRead]:
    repo = BookingRepository(db, org_id)
    return await repo.get_multi(skip=skip, limit=limit)


@router.post("/", response_model=BookingRead, status_code=201)
async def create_booking(
    data: BookingCreate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> BookingRead:
    prop_repo = PropertyRepository(db, org_id)
    prop = await prop_repo.get(data.property_id)
    if not prop or prop.is_archived:
        raise HTTPException(status_code=404, detail="Property not found")

    if data.guest_id:
        user_repo = UserRepository(db, org_id)
        guest = await user_repo.get(data.guest_id)
        if not guest:
            raise HTTPException(status_code=404, detail="Guest not found")

    repo = BookingRepository(db, org_id)
    obj_in = data.model_dump(exclude_unset=True)
    line_items_data = obj_in.pop("line_items_data", None)
    if "org_id" in obj_in and obj_in["org_id"] is None:
        del obj_in["org_id"]

    try:
        booking = await repo.create_with_line_items(obj_in, line_items_data)
    except IntegrityError as exc:
        await db.rollback()
        if "uq_booking_org_idempotency" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Booking with this idempotency key already exists",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database integrity error",
        )

    return booking


@router.post("/init", response_model=BookingInitResponse, status_code=201)
async def init_booking(
    data: BookingInitRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
    org_id: uuid.UUID = Depends(get_org_id),
) -> BookingInitResponse:
    svc = BookingInitService(db, org_id, redis_client)
    try:
        return await svc.init_booking(data)
    except BookingConflictError as exc:
        response = BookingConflictResponse(
            detail=str(exc),
            alternatives=exc.alternatives,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=response.model_dump(mode="json"),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )


@router.post("/{booking_id}/retry-payment", response_model=BookingInitResponse)
async def retry_payment(
    booking_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
    org_id: uuid.UUID = Depends(get_org_id),
) -> BookingInitResponse:
    svc = BookingInitService(db, org_id, redis_client)
    try:
        return await svc.retry_payment(booking_id)
    except BookingConflictError as exc:
        response = BookingConflictResponse(
            detail=str(exc),
            alternatives=exc.alternatives,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=response.model_dump(mode="json"),
        )
    except ValueError as exc:
        detail = str(exc)
        if "Maximum retry attempts exceeded" in detail:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=detail,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )


@router.patch("/{booking_id}/modify", response_model=BookingModificationResponse)
async def modify_booking(
    booking_id: uuid.UUID,
    data: BookingModificationRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
    org_id: uuid.UUID = Depends(get_org_id),
) -> BookingModificationResponse:
    svc = BookingModificationService(db, org_id, redis_client, actor_user_id=None)
    try:
        result = await svc.modify_booking(booking_id, data.model_dump(exclude_unset=True))
    except BookingConflictError as exc:
        response = BookingConflictResponse(
            detail=str(exc),
            alternatives=exc.alternatives,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=response.model_dump(mode="json"),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    booking = result["booking"]
    booking_dict = BookingRead.model_validate(booking).model_dump()
    booking_dict["payment_difference"] = result["payment_difference"]
    booking_dict["new_total"] = result["new_total"]
    booking_dict["razorpay_order"] = result.get("razorpay_order")
    booking_dict["refund_amount"] = result.get("refund_amount")
    return BookingModificationResponse(**booking_dict)


# Static paths MUST be registered before the dynamic /{booking_id} path
@router.get("/by-guest/{guest_id}", response_model=List[BookingRead])
async def list_bookings_by_guest(
    guest_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> List[BookingRead]:
    repo = BookingRepository(db, org_id)
    return await repo.get_by_guest(guest_id, skip=skip, limit=limit)


@router.get("/by-property/{property_id}", response_model=List[BookingRead])
async def list_bookings_by_property(
    property_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> List[BookingRead]:
    repo = BookingRepository(db, org_id)
    return await repo.get_by_property(property_id, skip=skip, limit=limit)


@router.get("/by-date-range", response_model=List[BookingRead])
async def list_bookings_by_date_range(
    check_in_from: date,
    check_in_to: date,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> List[BookingRead]:
    repo = BookingRepository(db, org_id)
    return await repo.get_by_date_range(
        check_in_from, check_in_to, skip=skip, limit=limit
    )


@router.get("/{booking_id}", response_model=BookingRead)
async def get_booking(
    booking_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> BookingRead:
    repo = BookingRepository(db, org_id)
    booking = await repo.get(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.patch("/{booking_id}", response_model=BookingRead)
async def update_booking(
    booking_id: uuid.UUID,
    data: BookingUpdate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> BookingRead:
    repo = BookingRepository(db, org_id)
    booking = await repo.get(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    update_data = data.model_dump(exclude_unset=True)
    new_status = update_data.get("status")
    if new_status:
        _validate_status_transition(booking.status, new_status)
        if new_status == BookingStatus.cancelled.value and not update_data.get("cancelled_at"):
            from datetime import datetime, timezone
            update_data["cancelled_at"] = datetime.now(timezone.utc)

    try:
        updated = await repo.update(booking, update_data)
    except IntegrityError as exc:
        await db.rollback()
        if "uq_booking_org_idempotency" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Booking with this idempotency key already exists",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database integrity error",
        )

    return updated


@router.delete("/{booking_id}", status_code=204)
async def delete_booking(
    booking_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> None:
    repo = BookingRepository(db, org_id)
    booking = await repo.get(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.status in {
        BookingStatus.cancelled.value,
        BookingStatus.completed.value,
    }:
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel a booking that is already cancelled or completed",
        )

    from datetime import datetime, timezone
    await repo.update(
        booking,
        {
            "status": BookingStatus.cancelled.value,
            "cancelled_at": datetime.now(timezone.utc),
        },
    )
