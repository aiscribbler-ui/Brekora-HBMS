"""Tests for Goibibo email parser."""
from datetime import date
from pathlib import Path

import pytest

from app.models.raw_email import RawEmail
from app.schemas.parsed_booking import ParsedBookingResult
from app.services.parsers.goibibo_parser import GoibiboParser

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "goibibo_emails"


def _load_fixture(filename: str) -> str:
    return (FIXTURES_DIR / filename).read_text(encoding="utf-8")


def _make_raw_email(*, body_text: str = "", body_html: str = "", subject: str = "Goibibo Booking") -> RawEmail:
    return RawEmail(
        id="test-id",  # type: ignore[arg-type]
        gmail_message_id="msg_gibo_001",
        ota_source="goibibo",
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        sender="bookings@goibibo.com",
        recipient="reservations@brekora.in",
        status="pending",
    )


@pytest.fixture
def parser() -> GoibiboParser:
    return GoibiboParser()


class TestGoibiboParseText:
    def test_parse_text_email(self, parser: GoibiboParser) -> None:
        body = _load_fixture("sample1.txt")
        raw = _make_raw_email(body_text=body)
        result = parser.parse(raw)

        assert result.ota_reference_id == "GIBO123456789"
        assert result.booking_reference == "GIBO123456789"
        assert result.hotel_id == "GHTL98765"
        assert result.room_details == "Deluxe Double Room"
        assert result.guest_name == "Ananya Rao"
        assert result.guest_email == "ananya.rao@example.com"
        assert result.check_in == date(2026, 5, 5)
        assert result.check_out == date(2026, 5, 8)
        assert result.number_of_guests == 2
        assert result.gross_amount == 9500.00
        assert result.ota_commission == 1425.00
        assert result.net_payout == 8075.00
        assert result.special_requests == "Late check-in requested"
        assert result.booking_date == date(2026, 4, 25)
        assert result.listing_id == "GHTL98765:GRM1234"
        assert result.needs_manual_review is False
        assert result.overall_confidence >= 0.8

    def test_confidence_scoring_text(self, parser: GoibiboParser) -> None:
        body = _load_fixture("sample1.txt")
        raw = _make_raw_email(body_text=body)
        result = parser.parse(raw)

        assert result.confidence_scores
        assert result.overall_confidence >= 0.8
        assert result.needs_manual_review is False


class TestGoibiboParseHTML:
    def test_parse_html_email(self, parser: GoibiboParser) -> None:
        body = _load_fixture("sample2.html")
        raw = _make_raw_email(body_html=body)
        result = parser.parse(raw)

        assert result.ota_reference_id == "GIBO987654321"
        assert result.booking_reference == "GIBO987654321"
        assert result.hotel_id == "GHTL54321"
        assert result.room_details == "Heritage Suite with Balcony"
        assert result.guest_name == "Vikram Mehta"
        assert result.guest_email == "vikram.mehta@example.com"
        assert result.check_in == date(2026, 5, 12)
        assert result.check_out == date(2026, 5, 15)
        assert result.number_of_guests == 4  # 3 Adults + 1 Child
        assert result.gross_amount == 18200.00
        assert result.ota_commission == 2730.00
        assert result.net_payout == 15470.00
        assert result.special_requests == "Ground floor room preferred"
        assert result.booking_date == date(2026, 4, 22)
        assert result.listing_id == "GHTL54321:GRM5678"
        assert result.needs_manual_review is False
        assert result.overall_confidence >= 0.8

    def test_confidence_scoring_html(self, parser: GoibiboParser) -> None:
        body = _load_fixture("sample2.html")
        raw = _make_raw_email(body_html=body)
        result = parser.parse(raw)

        assert result.confidence_scores
        assert result.overall_confidence >= 0.8
        assert result.needs_manual_review is False


class TestGoibiboParseEdgeCases:
    def test_missing_fields_handling(self, parser: GoibiboParser) -> None:
        raw = _make_raw_email(body_text="Hello from Goibibo. No booking details here.")
        result = parser.parse(raw)

        assert result.ota_reference_id is None
        assert result.check_in is None
        assert result.check_out is None
        assert result.gross_amount is None
        assert result.overall_confidence < 0.8
        assert result.needs_manual_review is True
        assert result.review_reason is not None
        assert "confidence" in result.review_reason.lower() or "missing" in result.review_reason.lower()

    def test_partial_fields_still_flags_review(self, parser: GoibiboParser) -> None:
        body = (
            "Booking Reference: GIBO999\n"
            "Check-in Date: 01 Jun 2026\n"
            "Check-out Date: 03 Jun 2026\n"
        )
        raw = _make_raw_email(body_text=body)
        result = parser.parse(raw)

        assert result.ota_reference_id == "GIBO999"
        assert result.check_in == date(2026, 6, 1)
        assert result.check_out == date(2026, 6, 3)
        assert result.needs_manual_review is True
        assert result.review_reason is not None

    def test_html_table_with_text_fallback(self, parser: GoibiboParser) -> None:
        html = (
            "<html><body><table>"
            "<tr><td>Booking Reference</td><td>GIBO777</td></tr>"
            "<tr><td>Check-in Date</td><td>05 Jun 2026</td></tr>"
            "</table></body></html>"
        )
        text = (
            "Check-out Date: 07 Jun 2026\n"
            "Guest Name: Amit Singh\n"
            "Total Amount: INR 5,000.00\n"
        )
        raw = _make_raw_email(body_html=html, body_text=text)
        result = parser.parse(raw)

        assert result.ota_reference_id == "GIBO777"
        assert result.check_in == date(2026, 6, 5)
        assert result.check_out == date(2026, 6, 7)
        assert result.guest_name == "Amit Singh"
        assert result.gross_amount == 5000.00

    def test_listing_id_fallback_to_names(self, parser: GoibiboParser) -> None:
        body = (
            "Hotel ID: GHTL111\n"
            "Room Type: Premium Cottage\n"
        )
        raw = _make_raw_email(body_text=body)
        result = parser.parse(raw)
        assert result.listing_id == "GHTL111|Premium Cottage"

    def test_number_of_guests_variants(self, parser: GoibiboParser) -> None:
        raw = _make_raw_email(body_text="Guests: 2 Adults")
        result = parser.parse(raw)
        assert result.number_of_guests == 2

        raw = _make_raw_email(body_text="Guests: 3 Adults, 2 Children")
        result = parser.parse(raw)
        assert result.number_of_guests == 5

    def test_date_parsing_variants(self, parser: GoibiboParser) -> None:
        variants = [
            "15 May 2026",
            "15-May-2026",
            "15/05/2026",
            "2026-05-15",
        ]
        for variant in variants:
            raw = _make_raw_email(body_text=f"Check-in Date: {variant}")
            result = parser.parse(raw)
            assert result.check_in == date(2026, 5, 15), f"Failed for {variant}"

    def test_amount_parsing_variants(self, parser: GoibiboParser) -> None:
        variants = [
            ("INR 12,500.00", 12500.00),
            ("Rs. 8400", 8400.00),
            ("₹1,260.00", 1260.00),
            ("2500", 2500.00),
        ]
        for raw_val, expected in variants:
            raw = _make_raw_email(body_text=f"Total Amount: {raw_val}")
            result = parser.parse(raw)
            assert result.gross_amount == expected, f"Failed for {raw_val}"

    def test_result_type(self, parser: GoibiboParser) -> None:
        body = _load_fixture("sample1.txt")
        raw = _make_raw_email(body_text=body)
        result = parser.parse(raw)
        assert isinstance(result, ParsedBookingResult)

    def test_to_canonical_dict(self, parser: GoibiboParser) -> None:
        body = _load_fixture("sample1.txt")
        raw = _make_raw_email(body_text=body)
        result = parser.parse(raw)
        d = result.model_dump()

        assert d["ota_reference_id"] == "GIBO123456789"
        assert d["check_in"] == date(2026, 5, 5)
        assert d["check_out"] == date(2026, 5, 8)
        assert d["gross_amount"] == 9500.00
        assert d["net_payout"] == 8075.00
        assert d["overall_confidence"] == result.overall_confidence
        assert d["needs_manual_review"] == result.needs_manual_review
