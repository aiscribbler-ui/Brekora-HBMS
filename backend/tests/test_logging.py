"""Tests for structured logging and correlation ID propagation."""
import ast
import contextlib
import json
import logging
from typing import Any, Generator

import pytest
from httpx import AsyncClient
from starlette.testclient import TestClient

from app.core.logging import configure_logging, get_logger, log_booking_cancelled, log_booking_created, log_payment_failed
from app.main import app


class LogCapture(logging.Handler):
    """Capture log records for assertions."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@contextlib.contextmanager
def capture_logs() -> Generator[LogCapture, None, None]:
    """Temporarily attach a LogCapture handler to the root logger."""
    handler = LogCapture()
    root = logging.getLogger()
    root.addHandler(handler)
    try:
        yield handler
    finally:
        root.removeHandler(handler)


class TestLogFormat:
    """Verify JSON structured log output contains required fields."""

    def test_json_log_contains_required_fields(self) -> None:
        configure_logging(json_logs=True, log_level="DEBUG")
        logger = get_logger("test.json")

        with capture_logs() as cap:
            logger.info("test_message", correlation_id="abc-123", user_id="user-42")

        assert len(cap.records) >= 1
        record = cap.records[-1]
        # ProcessorFormatter replaces record.msg with the rendered string;
        # getMessage() returns the formatted output after the stdlib formatter runs.
        raw = record.getMessage()
        parsed: dict[str, Any] = ast.literal_eval(raw)

        assert "timestamp" in parsed or "ts" in parsed
        assert parsed.get("event") == "test_message" or parsed.get("message") == "test_message"
        assert "log_level" in parsed or "level" in parsed
        assert parsed.get("correlation_id") == "abc-123"
        assert parsed.get("user_id") == "user-42"

    def test_console_log_in_dev(self) -> None:
        configure_logging(json_logs=False, log_level="DEBUG")
        logger = get_logger("test.console")

        with capture_logs() as cap:
            logger.info("hello_console")

        assert len(cap.records) >= 1
        record = cap.records[-1]
        # ConsoleRenderer produces plain text; just ensure it doesn't crash
        assert "hello_console" in str(record.getMessage())


class TestBusinessEventLogging:
    """Verify business-event helpers emit correct event types."""

    def test_log_booking_created(self) -> None:
        configure_logging(json_logs=True, log_level="DEBUG")

        with capture_logs() as cap:
            log_booking_created(
                booking_id="bk-001",
                user_id="u-01",
                org_id="org-01",
                property_id="prop-01",
                total_amount=4999.0,
                source="direct",
            )

        record = cap.records[-1]
        parsed: dict[str, Any] = ast.literal_eval(record.getMessage())
        assert parsed.get("event_type") == "booking_created"
        assert parsed.get("booking_id") == "bk-001"
        assert parsed.get("total_amount") == 4999.0

    def test_log_payment_failed(self) -> None:
        configure_logging(json_logs=True, log_level="DEBUG")

        with capture_logs() as cap:
            log_payment_failed(
                booking_id="bk-002",
                user_id="u-02",
                amount=2500.0,
                reason="insufficient_funds",
                payment_provider="razorpay",
            )

        record = cap.records[-1]
        parsed: dict[str, Any] = ast.literal_eval(record.getMessage())
        assert parsed.get("event_type") == "payment_failed"
        assert parsed.get("reason") == "insufficient_funds"
        assert parsed.get("level") == "warning"

    def test_log_booking_cancelled(self) -> None:
        configure_logging(json_logs=True, log_level="DEBUG")

        with capture_logs() as cap:
            log_booking_cancelled(
                booking_id="bk-003",
                user_id="u-03",
                cancellation_reason="guest_request",
                refund_amount=4999.0,
            )

        record = cap.records[-1]
        parsed: dict[str, Any] = ast.literal_eval(record.getMessage())
        assert parsed.get("event_type") == "booking_cancelled"
        assert parsed.get("refund_amount") == 4999.0


class TestCorrelationIdMiddleware:
    """Verify correlation ID propagation in request/response headers."""

    def test_generates_correlation_id_when_missing(self) -> None:
        client = TestClient(app)
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers
        assert len(response.headers["X-Correlation-ID"]) > 0

    def test_propagates_existing_correlation_id(self) -> None:
        client = TestClient(app)
        response = client.get(
            "/api/v1/health", headers={"X-Correlation-ID": "existing-cid-123"}
        )
        assert response.status_code == 200
        assert response.headers["X-Correlation-ID"] == "existing-cid-123"

    @pytest.mark.asyncio
    async def test_async_client_correlation_id(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers
