"""Tests for Gmail poller background task."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import DEFAULT_BREKORA_ORG_ID
from app.repositories.raw_email import RawEmailRepository
from app.tasks.gmail_poller import (
    BMS_PROCESSED_LABEL,
    GMAIL_QUERY,
    MAX_EMAILS_PER_POLL,
    _decode_body,
    _extract_body_parts,
    _get_ota_source,
    gmail_poller,
)


class FakeSessionContext:
    """Async context manager that yields a mock session."""

    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *args):
        pass


def test_decode_body():
    import base64

    original = "Hello, World!"
    encoded = base64.urlsafe_b64encode(original.encode()).decode()
    assert _decode_body(encoded) == original


def test_decode_body_empty():
    assert _decode_body("") == ""
    assert _decode_body(None) == ""


def test_get_ota_source():
    assert _get_ota_source("booking@airbnb.com") == "airbnb"
    assert _get_ota_source("noreply@makemytrip.com") == "mmt"
    assert _get_ota_source("confirm@goibibo.com") == "goibibo"
    assert _get_ota_source("spam@example.com") == "unknown"


def test_extract_body_parts_text():
    payload = {
        "mimeType": "text/plain",
        "body": {"data": "SGVsbG8gV29ybGQh"},
    }
    text, html = _extract_body_parts(payload)
    assert text == "Hello World!"
    assert html == ""


def test_extract_body_parts_html():
    payload = {
        "mimeType": "text/html",
        "body": {"data": "PGh0bWw+SGk8L2h0bWw-"},
    }
    text, html = _extract_body_parts(payload)
    assert text == ""
    assert html == "<html>Hi</html>"


def test_extract_body_parts_multipart():
    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {
                "mimeType": "text/plain",
                "body": {"data": "cGxhaW4gdGV4dA=="},
            },
            {
                "mimeType": "text/html",
                "body": {"data": "PGh0bWw+aHRtbDwvaHRtbD4="},
            },
        ],
    }
    text, html = _extract_body_parts(payload)
    assert text == "plain text"
    assert html == "<html>html</html>"


@pytest.mark.asyncio
async def test_gmail_poller_no_credentials():
    """When no Gmail credentials are available, poller returns ok with 0 processed."""
    ctx = {}
    with patch(
        "app.tasks.gmail_poller.GmailOAuthService.get_credentials",
        return_value=None,
    ):
        result = await gmail_poller(ctx)
    assert result["status"] == "ok"
    assert result["processed"] == 0
    assert "checked_at" in result
    assert "correlation_id" in result


@pytest.mark.asyncio
async def test_gmail_poller_no_messages():
    """When no messages are found, poller returns ok with 0 processed."""
    ctx = {}
    mock_credentials = MagicMock()
    mock_service = MagicMock()
    mock_list = MagicMock()
    mock_list.execute.return_value = {"messages": []}
    mock_service.users().messages().list.return_value = mock_list

    with patch(
        "app.tasks.gmail_poller.GmailOAuthService.get_credentials",
        return_value=mock_credentials,
    ):
        with patch("app.tasks.gmail_poller.build", return_value=mock_service):
            result = await gmail_poller(ctx)

    assert result["status"] == "ok"
    assert result["processed"] == 0


@pytest.mark.asyncio
async def test_gmail_poller_processes_and_stores_email(db_session):
    """Poller fetches email, stores it in DB, and marks as read."""
    ctx = {"session_factory": lambda: FakeSessionContext(db_session)}

    mock_credentials = MagicMock()

    mock_list = MagicMock()
    mock_list.execute.return_value = {"messages": [{"id": "msg123"}]}

    mock_get = MagicMock()
    mock_get.execute.return_value = {
        "id": "msg123",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Booking confirmed"},
                {"name": "From", "value": "booking@airbnb.com"},
                {"name": "To", "value": "brekora@gmail.com"},
                {"name": "Date", "value": "Mon, 30 Apr 2026 10:00:00 +0000"},
            ],
            "mimeType": "multipart/alternative",
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {"data": "cGxhaW4gYm9keQ=="},
                },
                {
                    "mimeType": "text/html",
                    "body": {"data": "PGh0bWw+Ym9keTwvaHRtbD4="},
                },
            ],
        },
    }

    mock_labels_list = MagicMock()
    mock_labels_list.execute.return_value = {
        "labels": [{"id": "label_1", "name": BMS_PROCESSED_LABEL}]
    }

    mock_modify = MagicMock()
    mock_modify.execute.return_value = {}

    mock_service = MagicMock()
    mock_service.users().messages().list.return_value = mock_list
    mock_service.users().messages().get.return_value = mock_get
    mock_service.users().labels().list.return_value = mock_labels_list
    mock_service.users().messages().modify.return_value = mock_modify

    with patch(
        "app.tasks.gmail_poller.GmailOAuthService.get_credentials",
        return_value=mock_credentials,
    ):
        with patch("app.tasks.gmail_poller.build", return_value=mock_service):
            result = await gmail_poller(ctx)

    assert result["status"] == "ok"
    # Email body has no parseable fields, so parser marks it as failed,
    # but the raw email is still stored and labels are modified.
    assert result["processed"] == 0
    assert result["failed"] == 1

    repo = RawEmailRepository(db_session, DEFAULT_BREKORA_ORG_ID)
    items = await repo.get_multi()
    assert any(i.gmail_message_id == "msg123" for i in items)
    email = next(i for i in items if i.gmail_message_id == "msg123")
    assert email.ota_source == "airbnb"
    assert email.ota_source == "airbnb"
    assert email.subject == "Booking confirmed"
    assert email.sender == "booking@airbnb.com"
    assert email.status == "pending"

    list_call = mock_service.users().messages().list.call_args
    assert list_call is not None
    assert list_call[1].get("q") == GMAIL_QUERY
    assert list_call[1].get("maxResults") == MAX_EMAILS_PER_POLL

    mock_service.users().messages().get.assert_called_once()
    mock_service.users().messages().modify.assert_called_once()
    modify_call = mock_service.users().messages().modify.call_args[1]
    assert "UNREAD" in modify_call["body"]["removeLabelIds"]
    assert "label_1" in modify_call["body"]["addLabelIds"]


@pytest.mark.asyncio
async def test_gmail_poller_continues_on_single_failure(db_session):
    """If one email fails to process, poller continues with the rest."""
    ctx = {"session_factory": lambda: FakeSessionContext(db_session)}

    mock_credentials = MagicMock()

    mock_list = MagicMock()
    mock_list.execute.return_value = {
        "messages": [{"id": "msg_good"}, {"id": "msg_bad"}]
    }

    def mock_get_side_effect(*args, **kwargs):
        message_id = kwargs.get("id", "")
        mock_get = MagicMock()
        if message_id == "msg_good":
            mock_get.execute.return_value = {
                "id": "msg_good",
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": "Good"},
                        {"name": "From", "value": "booking@makemytrip.com"},
                        {"name": "To", "value": "brekora@gmail.com"},
                        {"name": "Date", "value": "Mon, 30 Apr 2026 10:00:00 +0000"},
                    ],
                    "mimeType": "text/plain",
                    "body": {"data": "Z29vZA=="},
                },
            }
        else:
            mock_get.execute.side_effect = Exception("Gmail API exploded")
        return mock_get

    mock_labels_list = MagicMock()
    mock_labels_list.execute.return_value = {
        "labels": [{"id": "label_1", "name": BMS_PROCESSED_LABEL}]
    }

    mock_modify = MagicMock()
    mock_modify.execute.return_value = {}

    mock_service = MagicMock()
    mock_service.users().messages().list.return_value = mock_list
    mock_service.users().messages().get.side_effect = mock_get_side_effect
    mock_service.users().labels().list.return_value = mock_labels_list
    mock_service.users().messages().modify.return_value = mock_modify

    with patch(
        "app.tasks.gmail_poller.GmailOAuthService.get_credentials",
        return_value=mock_credentials,
    ):
        with patch("app.tasks.gmail_poller.build", return_value=mock_service):
            result = await gmail_poller(ctx)

    assert result["status"] == "ok"
    # msg_bad explodes (API error) → failed +=1
    # msg_good body has no parseable fields → parser missing_fields → failed +=1
    assert result["processed"] == 0
    assert result["failed"] == 2

    repo = RawEmailRepository(db_session, DEFAULT_BREKORA_ORG_ID)
    items = await repo.get_multi()
    assert any(i.gmail_message_id == "msg_good" for i in items)
    assert not any(i.gmail_message_id == "msg_bad" for i in items)


@pytest.mark.asyncio
async def test_gmail_poller_api_error(db_session):
    """When Gmail API list fails, poller returns gmail_api_error."""
    ctx = {}
    mock_credentials = MagicMock()

    mock_list = MagicMock()
    from googleapiclient.errors import HttpError

    mock_list.execute.side_effect = HttpError(
        resp=MagicMock(status=500),
        content=b"Internal error",
    )

    mock_service = MagicMock()
    mock_service.users().messages().list.return_value = mock_list

    with patch(
        "app.tasks.gmail_poller.GmailOAuthService.get_credentials",
        return_value=mock_credentials,
    ):
        with patch("app.tasks.gmail_poller.build", return_value=mock_service):
            result = await gmail_poller(ctx)

    assert result["status"] == "gmail_api_error"
    assert result["processed"] == 0
