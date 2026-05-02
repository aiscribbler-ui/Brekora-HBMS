"""Tests for Airbnb email parser."""

import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.models.raw_email import RawEmail
from app.services.parsers.airbnb_parser import AirbnbParser, ParsedBookingResult, _strip_html

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "airbnb_emails"


def _load_fixture(filename: str) -> str:
    return (FIXTURES_DIR / filename).read_text(encoding="utf-8")


def _make_raw_email(*, body_text: str | None = None, body_html: str | None = None) -> RawEmail:
    """Create a minimal RawEmail instance for parser testing."""
    return RawEmail(
        id=uuid.uuid4(),
        gmail_message_id="test_msg_123",
        ota_source="airbnb",
        subject="Reservation confirmed",
        body_text=body_text,
        body_html=body_html,
        sender="booking@airbnb.com",
        recipient="host@brekora.com",
        status="pending",
    )


# ---------------------------------------------------------------------------
# Fixture loading / HTML stripper
# ---------------------------------------------------------------------------


def test_strip_html_basic():
    html = "<html><body><p>Hello</p><div>World</div></body></html>"
    text = _strip_html(html)
    assert "Hello" in text
    assert "World" in text
    assert "<p>" not in text


def test_strip_html_preserves_whitespace():
    html = "<div>Line 1</div><div>Line 2</div>"
    text = _strip_html(html)
    assert "Line 1" in text
    assert "Line 2" in text


# ---------------------------------------------------------------------------
# Sample 1 — text-only Airbnb confirmation
# ---------------------------------------------------------------------------


def test_parse_text_email_sample1():
    raw = _load_fixture("sample1.txt")
    email = _make_raw_email(body_text=raw)
    parser = AirbnbParser()
    result = parser.parse(email)

    assert isinstance(result, ParsedBookingResult)
    assert result.ota_source == "airbnb"
    assert result.ota_reference_id == "HM8K3Z9A"
    assert result.guest_name == "Sarah Johnson"
    assert result.check_in == date(2025, 4, 27)
    assert result.check_out == date(2025, 4, 29)
    assert result.number_of_guests == 2
    assert result.listing_id == "88445521"
    assert result.room_type == "Mountain View Cottage in Manali"
    assert result.gross_amount == Decimal("12000.00")
    assert result.ota_commission == Decimal("1800.00")
    assert result.net_payout == Decimal("10200.00")
    assert result.booking_date == date(2025, 4, 15)
    assert result.special_requests is not None
    assert "extra blanket" in result.special_requests.lower()


# ---------------------------------------------------------------------------
# Sample 2 — HTML Airbnb confirmation
# ---------------------------------------------------------------------------


def test_parse_html_email_sample2():
    raw = _load_fixture("sample2.txt")
    email = _make_raw_email(body_html=raw)
    parser = AirbnbParser()
    result = parser.parse(email)

    assert isinstance(result, ParsedBookingResult)
    assert result.ota_reference_id == "RAHUL2025"
    assert result.guest_name == "Rahul Sharma"
    assert result.guest_email == "rahul.sharma@example.com"
    assert result.check_in == date(2025, 5, 2)
    assert result.check_out == date(2025, 5, 4)
    assert result.number_of_guests == 4
    assert result.listing_id == "99223344"
    assert result.room_type == "Valley Retreat in Kasol"
    assert result.gross_amount == Decimal("24500.00")
    assert result.ota_commission == Decimal("3675.00")
    assert result.net_payout == Decimal("20825.00")
    assert result.booking_date == date(2025, 4, 20)
    assert result.special_requests is not None
    assert "anniversary" in result.special_requests.lower()


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------


def test_confidence_scores_are_populated():
    raw = _load_fixture("sample1.txt")
    email = _make_raw_email(body_text=raw)
    result = AirbnbParser().parse(email)

    assert result.overall_confidence > 0.8
    assert result.needs_review is False

    # All critical fields should have non-zero confidence
    for field in AirbnbParser.CRITICAL_FIELDS:
        assert result.field_confidences.get(field, 0.0) > 0, f"{field} confidence is zero"


def test_confidence_high_for_complete_email():
    raw = _load_fixture("sample2.txt")
    email = _make_raw_email(body_html=raw)
    result = AirbnbParser().parse(email)

    assert result.overall_confidence >= 0.9
    assert result.needs_review is False
    assert result.review_reason == ""


# ---------------------------------------------------------------------------
# Missing / partial fields handling
# ---------------------------------------------------------------------------


def test_missing_fields_graceful():
    minimal_text = """
    Confirmation code: XYZ123
    Check-in: 2025-06-01
    Check-out: 2025-06-03
    Total: ₹5000
    You earn: ₹4000
    """
    email = _make_raw_email(body_text=minimal_text)
    result = AirbnbParser().parse(email)

    assert result.ota_reference_id == "XYZ123"
    assert result.check_in == date(2025, 6, 1)
    assert result.check_out == date(2025, 6, 3)
    assert result.gross_amount == Decimal("5000")
    assert result.net_payout == Decimal("4000")
    # Optional fields may be None
    assert result.guest_name is None
    assert result.special_requests is None
    assert result.booking_date is None


def test_empty_email_flags_review():
    email = _make_raw_email(body_text="", body_html=None)
    result = AirbnbParser().parse(email)

    assert result.overall_confidence == 0.0
    assert result.needs_review is True
    assert "No parseable text" in result.review_reason


# ---------------------------------------------------------------------------
# Low confidence flagging (< 0.8)
# ---------------------------------------------------------------------------


def test_low_confidence_flagged():
    sparse_text = """
    Hello,
    This is an Airbnb booking confirmation.
    Booking reference might be ABC999.
    Dates: sometime in July.
    """
    email = _make_raw_email(body_text=sparse_text)
    result = AirbnbParser().parse(email)

    assert result.overall_confidence < 0.8
    assert result.needs_review is True
    assert "Missing critical fields" in result.review_reason


def test_critical_fields_missing_causes_review():
    # Only confirmation code, no dates or amounts
    bad_text = "Confirmation code: ONLYME"
    email = _make_raw_email(body_text=bad_text)
    result = AirbnbParser().parse(email)

    assert result.needs_review is True
    assert result.ota_reference_id == "ONLYME"
    assert result.overall_confidence < 0.8


# ---------------------------------------------------------------------------
# to_canonical_dict serialization
# ---------------------------------------------------------------------------


def test_to_canonical_dict():
    raw = _load_fixture("sample1.txt")
    email = _make_raw_email(body_text=raw)
    result = AirbnbParser().parse(email)
    d = result.to_canonical_dict()

    assert d["ota_source"] == "airbnb"
    assert d["ota_reference_id"] == "HM8K3Z9A"
    assert d["check_in"] == "2025-04-27"
    assert d["check_out"] == "2025-04-29"
    assert d["gross_amount"] == "12000.00"
    assert d["net_payout"] == "10200.00"
    assert d["overall_confidence"] == result.overall_confidence
    assert d["needs_review"] == result.needs_review


# ---------------------------------------------------------------------------
# HTML fallback extraction
# ---------------------------------------------------------------------------


def test_html_body_used_when_text_missing():
    raw = _load_fixture("sample2.txt")
    email = _make_raw_email(body_text=None, body_html=raw)
    result = AirbnbParser().parse(email)

    # Should still extract everything from stripped HTML
    assert result.ota_reference_id == "RAHUL2025"
    assert result.guest_name == "Rahul Sharma"
    assert result.gross_amount == Decimal("24500.00")


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_date_parsing_various_formats():
    from app.services.parsers.airbnb_parser import _parse_date

    assert _parse_date("Sunday, April 27, 2025") == date(2025, 4, 27)
    assert _parse_date("27 Apr 2025") == date(2025, 4, 27)
    assert _parse_date("2025-04-27") == date(2025, 4, 27)
    assert _parse_date("04/27/2025") == date(2025, 4, 27)
    assert _parse_date("no date here") is None


def test_amount_parsing():
    from app.services.parsers.airbnb_parser import _parse_amount

    assert _parse_amount("₹12,000.00") == Decimal("12000.00")
    assert _parse_amount("$1,234.56") == Decimal("1234.56")
    assert _parse_amount("Total: ₹5000") == Decimal("5000")
    assert _parse_amount("") is None
