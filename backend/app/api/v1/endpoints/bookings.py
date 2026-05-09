import uuid
from datetime import date, timedelta
from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.redis import get_redis_client
from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.booking import BookingStatus
from app.models.user import User
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
from app.exceptions import BookingConflictError, ConflictError, InventoryError
from app.schemas.conflict import BookingConflictResponse
from app.services.booking_service import BookingInitService
from app.services.booking_modification_service import BookingModificationService
from app.models.inventory_hold import InventoryHold
from app.services.inventory_service import InventoryService

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


@router.get(
    "/",
    response_model=List[BookingRead],
    dependencies=[Depends(require_role(["Admin", "Manager", "Owner", "Partner"]))],
)
async def list_bookings(
    skip: int = 0,
    limit: int = 100,
    status: str | None = None,
    check_in_from: date | None = None,
    check_in_to: date | None = None,
    check_out_from: date | None = None,
    check_out_to: date | None = None,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
    current_user: User = Depends(get_current_user),
) -> List[BookingRead]:
    repo = BookingRepository(db, org_id)
    return await repo.get_filtered(
        skip=skip,
        limit=limit,
        status=status,
        check_in_from=check_in_from,
        check_in_to=check_in_to,
        check_out_from=check_out_from,
        check_out_to=check_out_to,
    )


@router.get("/summary", response_model=dict)
async def bookings_summary(
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
    current_user: User = Depends(get_current_user),
) -> dict:
    today = date.today()
    repo = BookingRepository(db, org_id)
    arrivals = await repo.count_by_check_in(today)
    departures = await repo.count_by_check_out(today)
    in_house = await repo.count_in_house(today)
    pending = await repo.count_by_status("pending_payment")
    return {
        "arrivals": arrivals,
        "departures": departures,
        "inHouse": in_house,
        "pendingCheckIns": pending,
    }


@router.post("/", response_model=BookingRead, status_code=201, dependencies=[])
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

    if line_items_data:
        for li in line_items_data:
            if li.get("item_type") == "room":
                inventory_svc = InventoryService(db)
                available = await inventory_svc.check_availability(
                    property_id=obj_in["property_id"],
                    room_type_id=li["item_id"],
                    check_in=obj_in["check_in"],
                    check_out=obj_in["check_out"],
                )
                if available < li.get("quantity", 1):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail={
                            "message": "Insufficient inventory for the requested dates",
                            "alternatives": [],
                        },
                    )

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

    # Atomically reserve inventory so concurrent staff bookings cannot overbook
    if line_items_data:
        inventory_svc = InventoryService(db)
        for li in line_items_data:
            if li.get("item_type") == "room":
                dates = [
                    booking.check_in + timedelta(days=i)
                    for i in range((booking.check_out - booking.check_in).days)
                ]
                try:
                    hold_id = await inventory_svc.hold_inventory(
                        booking_id=booking.id,
                        property_id=booking.property_id,
                        room_type_id=li["item_id"],
                        dates=dates,
                    )
                    await inventory_svc.commit_inventory(hold_id)
                except (ValueError, InventoryError, ConflictError) as exc:
                    await db.delete(booking)
                    await db.commit()
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail={
                            "message": f"Insufficient inventory: {exc}",
                            "alternatives": [],
                        },
                    )

    return booking


@router.post("/init", response_model=BookingInitResponse, status_code=201, dependencies=[])
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
    current_user: User = Depends(get_current_user),
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


@router.patch(
    "/{booking_id}/modify",
    response_model=BookingModificationResponse,
    dependencies=[Depends(require_role(["Admin", "Manager", "Owner", "Partner"]))],
)
async def modify_booking(
    booking_id: uuid.UUID,
    data: BookingModificationRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
    org_id: uuid.UUID = Depends(get_org_id),
    current_user: User = Depends(get_current_user),
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
@router.get(
    "/by-guest/{guest_id}",
    response_model=List[BookingRead],
    dependencies=[Depends(require_role(["Admin", "Manager", "Owner", "Partner"]))],
)
async def list_bookings_by_guest(
    guest_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
    current_user: User = Depends(get_current_user),
) -> List[BookingRead]:
    repo = BookingRepository(db, org_id)
    return await repo.get_by_guest(guest_id, skip=skip, limit=limit)


@router.get(
    "/by-property/{property_id}",
    response_model=List[BookingRead],
    dependencies=[Depends(require_role(["Admin", "Manager", "Owner", "Partner"]))],
)
async def list_bookings_by_property(
    property_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
    current_user: User = Depends(get_current_user),
) -> List[BookingRead]:
    repo = BookingRepository(db, org_id)
    return await repo.get_by_property(property_id, skip=skip, limit=limit)


@router.get(
    "/by-date-range",
    response_model=List[BookingRead],
    dependencies=[Depends(require_role(["Admin", "Manager", "Owner", "Partner"]))],
)
async def list_bookings_by_date_range(
    check_in_from: date,
    check_in_to: date,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
) -> BookingRead:
    repo = BookingRepository(db, org_id)
    booking = await repo.get(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.patch(
    "/{booking_id}",
    response_model=BookingRead,
    dependencies=[Depends(require_role(["Admin", "Manager", "Owner", "Partner"]))],
)
async def update_booking(
    booking_id: uuid.UUID,
    data: BookingUpdate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
    current_user: User = Depends(get_current_user),
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
            now = datetime.now(timezone.utc)
            update_data["cancelled_at"] = now

            # Release any active or committed inventory holds
            hold_stmt = select(InventoryHold).where(
                InventoryHold.booking_id == booking_id,
                InventoryHold.status.in_(("active", "committed")),
            )
            hold_result = await db.execute(hold_stmt)
            holds = hold_result.scalars().all()
            if holds:
                inventory_svc = InventoryService(db, None)
                for hold in holds:
                    try:
                        await inventory_svc.release_inventory(hold.id)
                    except Exception:
                        pass  # idempotent

            # Append cancellation entry to modification_log
            modification_log: list[dict] = []
            if booking.modification_log:
                modification_log = list(booking.modification_log)
            cancellation_reason = update_data.get("cancellation_reason", "Booking cancelled")
            audit_entry = {
                "timestamp": now.isoformat(),
                "actor_user_id": None,
                "changes": {
                    "status": {"old": booking.status, "new": BookingStatus.cancelled.value},
                    "cancelled_at": {
                        "old": booking.cancelled_at.isoformat() if booking.cancelled_at else None,
                        "new": now.isoformat(),
                    },
                },
                "reason": f"Booking cancelled: {cancellation_reason}",
            }
            modification_log.append(audit_entry)
            update_data["modification_log"] = modification_log

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


@router.delete(
    "/{booking_id}",
    status_code=204,
    dependencies=[Depends(require_role(["Admin", "Manager", "Owner", "Partner"]))],
)
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

    # Release any active or committed inventory holds
    hold_stmt = select(InventoryHold).where(
        InventoryHold.booking_id == booking_id,
        InventoryHold.status.in_(("active", "committed")),
    )
    hold_result = await db.execute(hold_stmt)
    holds = hold_result.scalars().all()
    if holds:
        inventory_svc = InventoryService(db, None)
        for hold in holds:
            try:
                await inventory_svc.release_inventory(hold.id)
            except Exception:
                pass  # idempotent

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    # Append cancellation entry to modification_log
    modification_log: list[dict] = []
    if booking.modification_log:
        modification_log = list(booking.modification_log)
    audit_entry = {
        "timestamp": now.isoformat(),
        "actor_user_id": None,
        "changes": {
            "status": {"old": booking.status, "new": BookingStatus.cancelled.value},
            "cancelled_at": {
                "old": booking.cancelled_at.isoformat() if booking.cancelled_at else None,
                "new": now.isoformat(),
            },
        },
        "reason": "Booking cancelled",
    }
    modification_log.append(audit_entry)

    await repo.update(
        booking,
        {
            "status": BookingStatus.cancelled.value,
            "cancelled_at": now,
            "modification_log": modification_log,
        },
    )
