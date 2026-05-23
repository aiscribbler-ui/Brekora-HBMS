"""Poll Gmail inbox for OTA booking confirmation emails."""
import base64
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from email.utils import parsedate_to_datetime

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import DEFAULT_BREKORA_ORG_ID, get_settings
from app.db.session import AsyncSessionLocal
from app.repositories.parsed_booking_queue import ParsedBookingQueueRepository
from app.repositories.raw_email import RawEmailRepository
from app.services.gmail_config_service import GmailConfigService
from app.services.gmail_oauth_service import GmailOAuthService
from app.services.ota_queue_service import OTAQueueService
from app.services.parse_metric_service import ParseMetricService
from app.services.parsers import PARSER_MAP

logger = logging.getLogger(__name__)

OTA_DOMAINS = {
    "airbnb.com": "airbnb",
    "makemytrip.com": "mmt",
    "goibibo.com": "goibibo",
}

GMAIL_QUERY = "is:unread from:(*@airbnb.com OR *@makemytrip.com OR *@goibibo.com)"
MAX_EMAILS_PER_POLL = 50
BMS_PROCESSED_LABEL = "BMS_PROCESSED"


def _get_ota_source(sender: str) -> str:
    """Map sender email domain to OTA source."""
    sender_lower = sender.lower()
    for domain, source in OTA_DOMAINS.items():
        if domain in sender_lower:
            return source
    return "unknown"


def _decode_body(data: str | None) -> str:
    """Decode base64url encoded Gmail message body."""
    if not data:
        return ""
    decoded_bytes = base64.urlsafe_b64decode(data)
    return decoded_bytes.decode("utf-8", errors="replace")


def _extract_headers(payload: dict) -> dict:
    """Extract common headers from Gmail message payload."""
    headers = payload.get("headers", [])
    result = {}
    for header in headers:
        name = header.get("name", "").lower()
        if name in ("subject", "from", "to", "date"):
            result[name] = header.get("value", "")
    return result


def _extract_body_parts(payload: dict) -> tuple[str, str]:
    """Extract text/plain and text/html body from Gmail message payload."""
    text = ""
    html = ""

    mime_type = payload.get("mimeType", "")
    body = payload.get("body", {})

    if mime_type == "text/plain" and "data" in body:
        text = _decode_body(body["data"])
    elif mime_type == "text/html" and "data" in body:
        html = _decode_body(body["data"])
    elif mime_type.startswith("multipart/"):
        parts = payload.get("parts", [])
        for part in parts:
            part_mime = part.get("mimeType", "")
            part_body = part.get("body", {})
            if part_mime == "text/plain" and "data" in part_body:
                text = _decode_body(part_body["data"])
            elif part_mime == "text/html" and "data" in part_body:
                html = _decode_body(part_body["data"])
            elif part_mime.startswith("multipart/"):
                sub_text, sub_html = _extract_body_parts(part)
                if sub_text and not text:
                    text = sub_text
                if sub_html and not html:
                    html = sub_html

    return text, html


def _parse_received_at(date_header: str) -> datetime | None:
    """Parse Date header into datetime."""
    if not date_header:
        return None
    try:
        dt = parsedate_to_datetime(date_header)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


async def _get_or_create_label(service, label_name: str) -> str | None:
    """Get existing label ID or create a new label."""
    try:
        labels_response = service.users().labels().list(userId="me").execute()
        labels = labels_response.get("labels", [])
        for label in labels:
            if label.get("name") == label_name:
                return label.get("id")

        create_body = {
            "name": label_name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        }
        new_label = (
            service.users().labels().create(userId="me", body=create_body).execute()
        )
        return new_label.get("id")
    except HttpError as exc:
        logger.warning("Failed to get/create label %s: %s", label_name, exc)
        return None


async def gmail_poller(ctx: dict) -> dict:
    """Poll Gmail inbox for OTA booking emails. Runs every 5 minutes."""
    correlation_id = str(uuid.uuid4())
    logger.info("gmail_poller started", extra={"correlation_id": correlation_id})

    settings = get_settings()
    session_factory = ctx.get("session_factory", AsyncSessionLocal)
    result = {
        "processed": 0,
        "failed": 0,
        "skipped": 0,
        "status": "ok",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "correlation_id": correlation_id,
    }

    async with session_factory() as config_session:
        config_svc = GmailConfigService(
            config_session,
            DEFAULT_BREKORA_ORG_ID,
            settings.GOOGLE_CLIENT_ID or "",
            settings.GOOGLE_CLIENT_SECRET or "",
        )
        oauth_service = GmailOAuthService(settings, config_svc)
        credentials = await oauth_service.get_credentials()

    if not credentials:
        logger.warning(
            "gmail_poller: no Gmail credentials available",
            extra={"correlation_id": correlation_id},
        )
        return result

    try:
        service = build("gmail", "v1", credentials=credentials, cache_discovery=False)

        search_response = (
            service.users()
            .messages()
            .list(userId="me", q=GMAIL_QUERY, maxResults=MAX_EMAILS_PER_POLL)
            .execute()
        )
        messages = search_response.get("messages", [])
        logger.info(
            "gmail_poller: found %s messages",
            len(messages),
            extra={"correlation_id": correlation_id},
        )

        if not messages:
            return result

        processed_label_id = await _get_or_create_label(service, BMS_PROCESSED_LABEL)

        async with session_factory() as session:
            repo = RawEmailRepository(session, DEFAULT_BREKORA_ORG_ID)

            for msg_meta in messages:
                message_id = msg_meta.get("id", "")
                try:
                    msg = (
                        service.users()
                        .messages()
                        .get(userId="me", id=message_id, format="full")
                        .execute()
                    )

                    payload = msg.get("payload", {})
                    headers = _extract_headers(payload)
                    subject = headers.get("subject", "")
                    sender = headers.get("from", "")
                    recipient = headers.get("to", "")
                    date_header = headers.get("date", "")
                    received_at = _parse_received_at(date_header)

                    body_text, body_html = _extract_body_parts(payload)
                    ota_source = _get_ota_source(sender)

                    raw_email = await repo.create(
                        {
                            "gmail_message_id": message_id,
                            "ota_source": ota_source,
                            "subject": subject,
                            "body_text": body_text,
                            "body_html": body_html,
                            "sender": sender,
                            "recipient": recipient,
                            "received_at": received_at,
                            "status": "pending",
                        }
                    )

                    logger.info(
                        "gmail_poller: stored raw_email message_id=%s source=%s id=%s",
                        message_id,
                        ota_source,
                        raw_email.id,
                        extra={"correlation_id": correlation_id},
                    )

                    # Parse and create queue entry
                    failure_reason = None
                    parse_success = False
                    parse_confidence = 0.0
                    parser_cls = PARSER_MAP.get(ota_source)
                    if not parser_cls:
                        failure_reason = f"unknown_ota: no parser available for source '{ota_source}'"
                    else:
                        try:
                            parser = parser_cls()
                            parsed_result = parser.parse(raw_email)

                            has_any_fields = (
                                parsed_result.ota_reference_id is not None
                                or parsed_result.check_in is not None
                                or parsed_result.check_out is not None
                                or parsed_result.gross_amount is not None
                            )
                            if not has_any_fields:
                                failure_reason = f"missing_fields: {parsed_result.review_reason or 'No critical fields extracted'}"
                            else:
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
                                parse_confidence = overall_confidence

                                queue_repo = ParsedBookingQueueRepository(session, DEFAULT_BREKORA_ORG_ID)
                                queue_item = await queue_repo.create(
                                    {
                                        "source_type": ota_source,
                                        "raw_email_id": raw_email.id,
                                        "ota_reference_id": parsed_result.ota_reference_id,
                                        "parsed_data": parsed_data,
                                        "confidence_score": Decimal(str(overall_confidence)),
                                        "status": "pending",
                                    }
                                )

                                logger.info(
                                    "gmail_poller: created queue item id=%s for raw_email id=%s",
                                    queue_item.id,
                                    raw_email.id,
                                    extra={"correlation_id": correlation_id},
                                )

                                queue_svc = OTAQueueService(session, DEFAULT_BREKORA_ORG_ID)
                                await queue_svc.process_auto_confirm(queue_item.id)
                                parse_success = True
                        except Exception as exc:
                            failure_reason = f"parser_error: {str(exc)}"

                    if failure_reason:
                        queue_repo = ParsedBookingQueueRepository(session, DEFAULT_BREKORA_ORG_ID)
                        await queue_repo.create(
                            {
                                "source_type": ota_source,
                                "raw_email_id": raw_email.id,
                                "parsed_data": {"failure_reason": failure_reason},
                                "confidence_score": Decimal("0.000"),
                                "status": "failed",
                                "review_notes": failure_reason,
                            }
                        )
                        logger.warning(
                            "gmail_poller: failed parse for message_id=%s reason=%s",
                            message_id,
                            failure_reason,
                            extra={"correlation_id": correlation_id},
                        )

                    # Record parser accuracy telemetry
                    try:
                        metric_service = ParseMetricService(session)
                        await metric_service.record_parse(
                            ota_source, parse_success, parse_confidence
                        )
                    except Exception as metric_exc:
                        logger.warning(
                            "gmail_poller: failed to record parse metric: %s",
                            metric_exc,
                            extra={"correlation_id": correlation_id},
                        )

                    modify_body = {"removeLabelIds": ["UNREAD"]}
                    if processed_label_id:
                        modify_body["addLabelIds"] = [processed_label_id]

                    service.users().messages().modify(
                        userId="me", id=message_id, body=modify_body
                    ).execute()

                    if failure_reason:
                        result["failed"] += 1
                    else:
                        result["processed"] += 1

                except Exception:
                    logger.exception(
                        "gmail_poller: failed to process message %s",
                        message_id,
                        extra={"correlation_id": correlation_id},
                    )
                    result["failed"] += 1

            await session.commit()

    except HttpError as exc:
        logger.error(
            "gmail_poller: Gmail API error %s",
            exc,
            extra={"correlation_id": correlation_id},
        )
        result["status"] = "gmail_api_error"
    except Exception:
        logger.exception(
            "gmail_poller: unexpected error",
            extra={"correlation_id": correlation_id},
        )
        result["status"] = "error"
        raise

    logger.info(
        "gmail_poller completed: %s",
        result,
        extra={"correlation_id": correlation_id},
    )
    return result
