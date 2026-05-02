"""Tests for MakeMyTrip email parser."""
from datetime import date
from pathlib import Path

import pytest

from app.models.raw_email import RawEmail
from app.schemas.parsed_booking import ParsedBookingResult
from app.services.parsers.mmt_parser import MMTParser

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "mmt_emails"


def _load_fixture(filename: str) -> str:
    return (FIXTURES_DIR / filename).read_text(encoding="utf-8")


def _make_raw_email(*, body_text: str = "", body_html: str = "", subject: str = "MMT Booking") -> RawEmail:
    return RawEmail(
        id="test-id",  # type: ignore[arg-type]
        gmail_message_id="msg_001",
        ota_source="mmt",
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        sender="noreply@makemytrip.com",
        recipient="reservations@brekora.in",
        status="pending",
    )


@pytest.fixture
def parser() -> MMTParser:
    return MMTParser()


class TestMMTParseText:
    def test_parse_text_email(self, parser: MMTParser) -> None:
        body = _load_fixture("sample1.txt")
        raw = _make_raw_email(body_text=body)
        result = parser.parse(raw)

        assert result.ota_reference_id == "BRN9876543210"
        assert result.voucher_number == "MMT1234567890"
        assert result.hotel_name == "The Grand Brekora"
        assert result.room_type_name == "Deluxe King Room"
        assert result.number_of_rooms == 2
        assert result.guest_name == "Rajesh Kumar"
        assert result.guest_email == "rajesh.kumar@example.com"
        assert result.check_in == date(2026, 5, 15)
        assert result.check_out == date(2026, 5, 18)
        assert result.number_of_guests == 4  # 3 Adults + 1 Child
        assert result.gross_amount == 12500.00
        assert result.ota_commission == 1875.00
        assert result.net_payout == 10625.00
        assert result.special_requests == "Early check-in requested"
        assert result.booking_date == date(2026, 5, 10)
        assert result.listing_id == "HTL98765:RM1234"
        assert result.needs_manual_review is False
        assert result.overall_confidence >= 0.8

    def test_confidence_scoring_text(self, parser: MMTParser) -> None:
        body = _load_fixture("sample1.txt")
        raw = _make_raw_email(body_text=body)
        result = parser.parse(raw)

        assert result.confidence_scores
        assert result.overall_confidence >= 0.8
        assert result.needs_manual_review is False


class TestMMTParseHTML:
    def test_parse_html_email(self, parser: MMTParser) -> None:
        body = _load_fixture("sample2.html")
        raw = _make_raw_email(body_html=body)
        result = parser.parse(raw)

        assert result.ota_reference_id == "BRN1122334455"
        assert result.voucher_number == "MMT9876543210"
        assert result.hotel_name == "Brekora Beach Resort"
        assert result.room_type_name == "Superior Sea View Room"
        assert result.number_of_rooms == 1
        assert result.guest_name == "Priya Sharma"
        assert result.guest_email == "priya.sharma@example.com"
        assert result.check_in == date(2026, 5, 20)
        assert result.check_out == date(2026, 5, 22)
        assert result.number_of_guests == 2
        assert result.gross_amount == 8400.00
        assert result.ota_commission == 1260.00
        assert result.net_payout == 7140.00
        assert result.special_requests == "Non-smoking room"
        assert result.booking_date == date(2026, 5, 18)
        assert result.listing_id == "HTL54321:RM5678"
        assert result.needs_manual_review is False
        assert result.overall_confidence >= 0.8

    def test_confidence_scoring_html(self, parser: MMTParser) -> None:
        body = _load_fixture("sample2.html")
        raw = _make_raw_email(body_html=body)
        result = parser.parse(raw)

        assert result.confidence_scores
        assert result.overall_confidence >= 0.8
        assert result.needs_manual_review is False


class TestMMTParseEdgeCases:
    def test_missing_fields_handling(self, parser: MMTParser) -> None:
        raw = _make_raw_email(body_text="Hello from MakeMyTrip. No booking details here.")
        result = parser.parse(raw)

        assert result.ota_reference_id is None
        assert result.check_in is None
        assert result.check_out is None
        assert result.gross_amount is None
        assert result.overall_confidence < 0.8
        assert result.needs_manual_review is True
        assert result.review_reason is not None
        assert "confidence" in result.review_reason.lower() or "missing" in result.review_reason.lower()

    def test_partial_fields_still_flags_review(self, parser: MMTParser) -> None:
        body = (
            "Booking Reference: BRN999\n"
            "Check-in Date: 01 Jun 2026\n"
            "Check-out Date: 03 Jun 2026\n"
        )
        raw = _make_raw_email(body_text=body)
        result = parser.parse(raw)

        assert result.ota_reference_id == "BRN999"
        assert result.check_in == date(2026, 6, 1)
        assert result.check_out == date(2026, 6, 3)
        # Missing many fields -> low confidence / missing amount
        assert result.needs_manual_review is True
        assert result.review_reason is not None

    def test_html_table_with_text_fallback(self, parser: MMTParser) -> None:
        # HTML has some fields, text has others; parser merges
        html = (
            "<html><body><table>"
            "<tr><td>Booking Reference</td><td>BRN777</td></tr>"
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

        assert result.ota_reference_id == "BRN777"
        assert result.check_in == date(2026, 6, 5)
        assert result.check_out == date(2026, 6, 7)
        assert result.guest_name == "Amit Singh"
        assert result.gross_amount == 5000.00

    def test_listing_id_fallback_to_names(self, parser: MMTParser) -> None:
        body = (
            "Hotel Name: Ocean View\n"
            "Room Type Name: Suite\n"
        )
        raw = _make_raw_email(body_text=body)
        result = parser.parse(raw)
        assert result.listing_id == "Ocean View|Suite"

    def test_number_of_guests_variants(self, parser: MMTParser) -> None:
        # Test "2 Adults" pattern
        raw = _make_raw_email(body_text="Guests: 2 Adults")
        result = parser.parse(raw)
        assert result.number_of_guests == 2

        # Test "3 Adults, 2 Children" pattern
        raw = _make_raw_email(body_text="Guests: 3 Adults, 2 Children")
        result = parser.parse(raw)
        assert result.number_of_guests == 5

    def test_date_parsing_variants(self, parser: MMTParser) -> None:
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

    def test_amount_parsing_variants(self, parser: MMTParser) -> None:
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

    def test_result_type(self, parser: MMTParser) -> None:
        body = _load_fixture("sample1.txt")
        raw = _make_raw_email(body_text=body)
        result = parser.parse(raw)
        assert isinstance(result, ParsedBookingResult)
