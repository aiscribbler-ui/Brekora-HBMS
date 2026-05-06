import uuid
from datetime import date
from typing import Any, List

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.parsed_booking_queue import (
    ParsedBookingQueueConfirmRequest,
    ParsedBookingQueueEditRequest,
    ParsedBookingQueueRead,
    ParsedBookingQueueRejectRequest,
)
from app.services.ota_queue_service import OTAQueueService

router = APIRouter()

settings = get_settings()
DEFAULT_ORG_ID = settings.DEFAULT_ORG_ID


def get_org_id(
    x_org_id: str | None = Header(default=None, alias="X-Org-ID"),
) -> uuid.UUID:
    if x_org_id:
        return uuid.UUID(x_org_id)
    return DEFAULT_ORG_ID


def _serialize_raw_email(raw_email) -> dict | None:
    if raw_email is None:
        return None
    return {
        "id": str(raw_email.id),
        "gmail_message_id": raw_email.gmail_message_id,
        "ota_source": raw_email.ota_source,
        "subject": raw_email.subject,
        "body_text": raw_email.body_text,
        "body_html": raw_email.body_html,
        "sender": raw_email.sender,
        "recipient": raw_email.recipient,
        "received_at": raw_email.received_at.isoformat() if raw_email.received_at else None,
        "status": raw_email.status,
    }


@router.get(
    "/",
    response_model=List[ParsedBookingQueueRead],
    dependencies=[Depends(require_role(["Admin", "Manager", "ListingManager"]))],
)
async def list_ota_queue(
    source_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> List[Any]:
    svc = OTAQueueService(db, org_id)
    return await svc.list_pending(
        source_type=source_type,
        status=status,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{queue_id}",
    dependencies=[Depends(require_role(["Admin", "Manager", "ListingManager"]))],
)
async def get_ota_queue_item(
    queue_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> Any:
    svc = OTAQueueService(db, org_id)
    details = await svc.get_details(queue_id)
    if not details:
        raise HTTPException(status_code=404, detail="Parsed booking not found")
    email_link = None
    if details["raw_email"] and details["raw_email"].gmail_message_id:
        email_link = f"https://mail.google.com/mail/u/0/#inbox/{details['raw_email'].gmail_message_id}"

    return {
        "parsed_booking": ParsedBookingQueueRead.model_validate(details["parsed_booking"]).model_dump(),
        "raw_email": _serialize_raw_email(details["raw_email"]),
        "email_link": email_link,
    }


@router.post(
    "/{queue_id}/confirm",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(["Admin", "Manager", "ListingManager"]))],
)
async def confirm_ota_queue_item(
    queue_id: uuid.UUID,
    data: ParsedBookingQueueConfirmRequest,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> Any:
    svc = OTAQueueService(db, org_id)
    # TODO: use real manager_id from auth when B-6 RBAC is wired
    manager_id = None
    try:
        booking = await svc.confirm(queue_id, data, manager_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return {"booking_id": booking.id, "status": "confirmed"}


@router.post(
    "/{queue_id}/edit",
    response_model=ParsedBookingQueueRead,
    dependencies=[Depends(require_role(["Admin", "Manager", "ListingManager"]))],
)
async def edit_ota_queue_item(
    queue_id: uuid.UUID,
    data: ParsedBookingQueueEditRequest,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> Any:
    svc = OTAQueueService(db, org_id)
    try:
        updated = await svc.edit(queue_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return updated


@router.post(
    "/{queue_id}/reject",
    response_model=ParsedBookingQueueRead,
    dependencies=[Depends(require_role(["Admin", "Manager", "ListingManager"]))],
)
async def reject_ota_queue_item(
    queue_id: uuid.UUID,
    data: ParsedBookingQueueRejectRequest,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> Any:
    svc = OTAQueueService(db, org_id)
    # TODO: use real manager_id from auth when B-6 RBAC is wired
    manager_id = None
    try:
        updated = await svc.reject(queue_id, data, manager_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return updated
