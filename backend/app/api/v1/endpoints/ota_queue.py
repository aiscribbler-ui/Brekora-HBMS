import uuid
from datetime import date
from decimal import Decimal
from typing import Any, List

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.models.user import User
from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.parsed_booking_queue import (
    ParsedBookingQueueConfirmRequest,
    ParsedBookingQueueEditRequest,
    ParsedBookingQueueRead,
    ParsedBookingQueueRejectRequest,
)
from app.services.ota_queue_service import OTAQueueService
from app.services.parsers import PARSER_MAP
from app.repositories.raw_email import RawEmailRepository
from app.repositories.parsed_booking_queue import ParsedBookingQueueRepository

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
    dependencies=[Depends(require_role(["Admin", "Manager", "ListingManager"]))],
)
async def list_ota_queue(
    source_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    max_confidence: Decimal | None = Query(default=None),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> Any:
    svc = OTAQueueService(db, org_id)
    return await svc.list_pending(
        source_type=source_type,
        status=status,
        date_from=date_from,
        date_to=date_to,
        max_confidence=max_confidence,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/stats",
    dependencies=[Depends(require_role(["Admin", "Manager", "ListingManager"]))],
)
async def get_ota_queue_stats(
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> Any:
    svc = OTAQueueService(db, org_id)
    return await svc.get_stats()


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
    current_user: User = Depends(get_current_user),
) -> Any:
    svc = OTAQueueService(db, org_id)
    manager_id = str(current_user.id)
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
    current_user: User = Depends(get_current_user),
) -> Any:
    svc = OTAQueueService(db, org_id)
    manager_id = str(current_user.id)
    try:
        updated = await svc.reject(queue_id, data, manager_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return updated


@router.post(
    "/reprocess/{raw_email_id}",
    dependencies=[Depends(require_role(["Admin", "Manager", "ListingManager"]))],
)
async def reprocess_raw_email(
    raw_email_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> Any:
    """Re-parse a raw email with the latest parser and update the queue entry."""
    raw_email_repo = RawEmailRepository(db, org_id)
    raw_email = await raw_email_repo.get(raw_email_id)
    if not raw_email:
        raise HTTPException(status_code=404, detail="Raw email not found")

    parser_cls = PARSER_MAP.get(raw_email.ota_source)
    if not parser_cls:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No parser available for source '{raw_email.ota_source}'",
        )

    parser = parser_cls()
    parsed_result = parser.parse(raw_email)

    has_any_fields = (
        parsed_result.ota_reference_id is not None
        or parsed_result.check_in is not None
        or parsed_result.check_out is not None
        or parsed_result.gross_amount is not None
    )
    if not has_any_fields:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Parser could not extract critical fields: {parsed_result.review_reason or 'No fields found'}",
        )

    parsed_data: dict = {}
    if parsed_result.ota_reference_id:
        parsed_data["ota_reference_id"] = parsed_result.ota_reference_id
    if parsed_result.guest_name:
        parsed_data["guest_name"] = parsed_result.guest_name
    if parsed_result.guest_email:
        parsed_data["guest_email"] = parsed_result.guest_email
    check_in = getattr(parsed_result, "check_in", None)
    if check_in:
        parsed_data["check_in"] = (
            check_in.isoformat() if hasattr(check_in, "isoformat") else str(check_in)
        )
    check_out = getattr(parsed_result, "check_out", None)
    if check_out:
        parsed_data["check_out"] = (
            check_out.isoformat() if hasattr(check_out, "isoformat") else str(check_out)
        )
    listing_id = getattr(parsed_result, "listing_id", None)
    if listing_id:
        parsed_data["listing_id"] = listing_id
    number_of_guests = getattr(parsed_result, "number_of_guests", None)
    if number_of_guests is not None:
        parsed_data["number_of_guests"] = number_of_guests
    gross_amount = getattr(parsed_result, "gross_amount", None)
    if gross_amount is not None:
        parsed_data["gross_amount"] = float(gross_amount)
    net_payout = getattr(parsed_result, "net_payout", None)
    if net_payout is not None:
        parsed_data["net_payout"] = float(net_payout)

    raw_payload = getattr(parsed_result, "raw_payload", None)
    if raw_payload:
        parsed_data.update(raw_payload)

    overall_confidence = getattr(parsed_result, "overall_confidence", 0.0)

    # Look for an existing queue entry tied to this raw email
    from sqlalchemy import select
    from app.models.parsed_booking import ParsedBookingQueue

    stmt = (
        select(ParsedBookingQueue)
        .where(ParsedBookingQueue.raw_email_id == raw_email_id)
        .where(ParsedBookingQueue.org_id == org_id)
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    queue_repo = ParsedBookingQueueRepository(db, org_id)
    if existing:
        queue_item = await queue_repo.update(
            existing,
            {
                "ota_reference_id": parsed_result.ota_reference_id,
                "parsed_data": parsed_data,
                "confidence_score": Decimal(str(overall_confidence)),
                "status": "pending",
                "review_notes": parsed_result.review_reason or None,
            },
        )
    else:
        queue_item = await queue_repo.create(
            {
                "source_type": raw_email.ota_source,
                "raw_email_id": raw_email.id,
                "ota_reference_id": parsed_result.ota_reference_id,
                "parsed_data": parsed_data,
                "confidence_score": Decimal(str(overall_confidence)),
                "status": "pending",
                "review_notes": parsed_result.review_reason or None,
            }
        )

    # Attempt auto-confirm if confidence is high enough
    queue_svc = OTAQueueService(db, org_id)
    await queue_svc.process_auto_confirm(queue_item.id)

    return {
        "queue_item_id": queue_item.id,
        "raw_email_id": raw_email.id,
        "confidence": overall_confidence,
        "needs_review": parsed_result.needs_review,
        "review_reason": parsed_result.review_reason,
        "parsed_data": parsed_data,
    }
