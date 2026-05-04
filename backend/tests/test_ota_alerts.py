"""Tests for failed parse alert endpoints."""
import uuid
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.parsed_booking import ParsedBookingQueue, ParsedBookingStatus
from app.repositories.parsed_booking_queue import ParsedBookingQueueRepository
from app.repositories.raw_email import RawEmailRepository

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def _create_raw_email(
    db_session: AsyncSession,
    ota_source: str = "airbnb",
    body_text: str = "test",
) -> uuid.UUID:
    repo = RawEmailRepository(db_session, DEFAULT_ORG_ID)
    email = await repo.create(
        {
            "gmail_message_id": f"msg_{uuid.uuid4().hex}",
            "ota_source": ota_source,
            "subject": "Test",
            "body_text": body_text,
            "sender": "test@example.com",
        }
    )
    return email.id


async def _create_failed_queue_item(
    db_session: AsyncSession,
    raw_email_id: uuid.UUID,
    source_type: str = "airbnb",
    review_notes: str = "parser_error: something failed",
) -> ParsedBookingQueue:
    repo = ParsedBookingQueueRepository(db_session, DEFAULT_ORG_ID)
    return await repo.create(
        {
            "source_type": source_type,
            "raw_email_id": raw_email_id,
            "parsed_data": {"failure_reason": review_notes},
            "confidence_score": Decimal("0.000"),
            "status": "failed",
            "review_notes": review_notes,
        }
    )


@pytest.mark.asyncio
async def test_list_failed_parses(client: AsyncClient, db_session: AsyncSession):
    raw_email_id = await _create_raw_email(db_session)
    item = await _create_failed_queue_item(db_session, raw_email_id)

    resp = await client.get("/api/v1/ota/alerts/")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(i["id"] == str(item.id) for i in data)
    assert all(i["status"] == "failed" for i in data)


@pytest.mark.asyncio
async def test_list_failed_parses_filter_by_source(client: AsyncClient, db_session: AsyncSession):
    raw_airbnb = await _create_raw_email(db_session, ota_source="airbnb")
    raw_mmt = await _create_raw_email(db_session, ota_source="mmt")
    item_airbnb = await _create_failed_queue_item(db_session, raw_airbnb, source_type="airbnb")
    item_mmt = await _create_failed_queue_item(db_session, raw_mmt, source_type="mmt")

    resp = await client.get("/api/v1/ota/alerts/?source_type=airbnb")
    assert resp.status_code == 200
    data = resp.json()
    ids = {i["id"] for i in data}
    assert str(item_airbnb.id) in ids
    assert str(item_mmt.id) not in ids


@pytest.mark.asyncio
async def test_count_failed_parses(client: AsyncClient, db_session: AsyncSession):
    raw1 = await _create_raw_email(db_session, ota_source="airbnb")
    raw2 = await _create_raw_email(db_session, ota_source="airbnb")
    raw3 = await _create_raw_email(db_session, ota_source="mmt")
    await _create_failed_queue_item(db_session, raw1, source_type="airbnb")
    await _create_failed_queue_item(db_session, raw2, source_type="airbnb")
    await _create_failed_queue_item(db_session, raw3, source_type="mmt")

    resp = await client.get("/api/v1/ota/alerts/count")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    counts = {entry["source_type"]: entry["count"] for entry in data}
    assert counts.get("airbnb") >= 2
    assert counts.get("mmt") >= 1


@pytest.mark.asyncio
async def test_retry_failed_parse_success(client: AsyncClient, db_session: AsyncSession):
    raw_email_id = await _create_raw_email(db_session)
    item = await _create_failed_queue_item(db_session, raw_email_id)

    fake_result = MagicMock()
    fake_result.ota_reference_id = "REF123"
    fake_result.guest_name = "Alice"
    fake_result.guest_email = "alice@example.com"
    fake_result.check_in = date.today() + timedelta(days=10)
    fake_result.check_out = date.today() + timedelta(days=12)
    fake_result.listing_id = "airbnb_123"
    fake_result.number_of_guests = 2
    fake_result.gross_amount = Decimal("2000.00")
    fake_result.net_payout = Decimal("1600.00")
    fake_result.raw_payload = None
    fake_result.overall_confidence = 0.95

    mock_parser_cls = MagicMock()
    mock_parser = MagicMock()
    mock_parser.parse.return_value = fake_result
    mock_parser_cls.return_value = mock_parser

    with patch("app.services.parse_alert_service.PARSER_MAP", {"airbnb": mock_parser_cls}):
        with patch(
            "app.services.parse_alert_service.OTAQueueService.process_auto_confirm",
            return_value=None,
        ):
            resp = await client.post(f"/api/v1/ota/alerts/{item.id}/retry")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pending"
    assert data["ota_reference_id"] == "REF123"


@pytest.mark.asyncio
async def test_retry_failed_parse_parser_exception(client: AsyncClient, db_session: AsyncSession):
    raw_email_id = await _create_raw_email(db_session)
    item = await _create_failed_queue_item(db_session, raw_email_id)

    mock_parser_cls = MagicMock()
    mock_parser = MagicMock()
    mock_parser.parse.side_effect = Exception("HTML is malformed")
    mock_parser_cls.return_value = mock_parser

    with patch("app.services.parse_alert_service.PARSER_MAP", {"airbnb": mock_parser_cls}):
        resp = await client.post(f"/api/v1/ota/alerts/{item.id}/retry")

    assert resp.status_code == 400
    data = resp.json()
    assert "Parser error" in data["detail"]


@pytest.mark.asyncio
async def test_retry_failed_parse_missing_fields(client: AsyncClient, db_session: AsyncSession):
    raw_email_id = await _create_raw_email(db_session)
    item = await _create_failed_queue_item(db_session, raw_email_id)

    fake_result = MagicMock()
    fake_result.ota_reference_id = None
    fake_result.check_in = None
    fake_result.check_out = None
    fake_result.gross_amount = None
    fake_result.review_reason = "No parseable text content found."

    mock_parser_cls = MagicMock()
    mock_parser = MagicMock()
    mock_parser.parse.return_value = fake_result
    mock_parser_cls.return_value = mock_parser

    with patch("app.services.parse_alert_service.PARSER_MAP", {"airbnb": mock_parser_cls}):
        resp = await client.post(f"/api/v1/ota/alerts/{item.id}/retry")

    assert resp.status_code == 400
    data = resp.json()
    assert "no critical fields extracted" in data["detail"]


@pytest.mark.asyncio
async def test_retry_non_failed_item(client: AsyncClient, db_session: AsyncSession):
    raw_email_id = await _create_raw_email(db_session)
    repo = ParsedBookingQueueRepository(db_session, DEFAULT_ORG_ID)
    item = await repo.create(
        {
            "source_type": "airbnb",
            "raw_email_id": raw_email_id,
            "status": "pending",
            "confidence_score": Decimal("0.95"),
        }
    )

    resp = await client.post(f"/api/v1/ota/alerts/{item.id}/retry")
    assert resp.status_code == 400
    assert "Can only retry failed alerts" in resp.json()["detail"]
