"""Standalone runner for MMT parser tests (bypasses pytest DB fixtures)."""
import sys
from datetime import date
from pathlib import Path

# Ensure backend is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.parsers.mmt_parser import MMTParser
from app.models.raw_email import RawEmail


def _load_fixture(filename: str) -> str:
    return (Path(__file__).parent / "fixtures" / "mmt_emails" / filename).read_text(encoding="utf-8")


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


def main() -> None:
    parser = MMTParser()
    errors = []

    # --- Test text email ---
    body = _load_fixture("sample1.txt")
    raw = _make_raw_email(body_text=body)
    result = parser.parse(raw)

    assert result.ota_reference_id == "BRN9876543210", errors.append("text: ota_reference_id")
    assert result.voucher_number == "MMT1234567890", errors.append("text: voucher_number")
    assert result.hotel_name == "The Grand Brekora", errors.append("text: hotel_name")
    assert result.room_type_name == "Deluxe King Room", errors.append("text: room_type_name")
    assert result.number_of_rooms == 2, errors.append("text: number_of_rooms")
    assert result.guest_name == "Rajesh Kumar", errors.append("text: guest_name")
    assert result.guest_email == "rajesh.kumar@example.com", errors.append("text: guest_email")
    assert result.check_in == date(2026, 5, 15), errors.append("text: check_in")
    assert result.check_out == date(2026, 5, 18), errors.append("text: check_out")
    assert result.number_of_guests == 4, errors.append("text: number_of_guests")
    assert result.gross_amount == 12500.00, errors.append("text: gross_amount")
    assert result.ota_commission == 1875.00, errors.append("text: ota_commission")
    assert result.net_payout == 10625.00, errors.append("text: net_payout")
    assert result.special_requests == "Early check-in requested", errors.append("text: special_requests")
    assert result.booking_date == date(2026, 5, 10), errors.append("text: booking_date")
    assert result.listing_id == "HTL98765:RM1234", errors.append("text: listing_id")
    assert result.needs_manual_review is False, errors.append("text: needs_manual_review")
    assert result.overall_confidence >= 0.8, errors.append("text: overall_confidence")

    # --- Test HTML email ---
    body = _load_fixture("sample2.html")
    raw = _make_raw_email(body_html=body)
    result = parser.parse(raw)

    assert result.ota_reference_id == "BRN1122334455", errors.append("html: ota_reference_id")
    assert result.voucher_number == "MMT9876543210", errors.append("html: voucher_number")
    assert result.hotel_name == "Brekora Beach Resort", errors.append("html: hotel_name")
    assert result.room_type_name == "Superior Sea View Room", errors.append("html: room_type_name")
    assert result.number_of_rooms == 1, errors.append("html: number_of_rooms")
    assert result.guest_name == "Priya Sharma", errors.append("html: guest_name")
    assert result.guest_email == "priya.sharma@example.com", errors.append("html: guest_email")
    assert result.check_in == date(2026, 5, 20), errors.append("html: check_in")
    assert result.check_out == date(2026, 5, 22), errors.append("html: check_out")
    assert result.number_of_guests == 2, errors.append("html: number_of_guests")
    assert result.gross_amount == 8400.00, errors.append("html: gross_amount")
    assert result.ota_commission == 1260.00, errors.append("html: ota_commission")
    assert result.net_payout == 7140.00, errors.append("html: net_payout")
    assert result.special_requests == "Non-smoking room", errors.append("html: special_requests")
    assert result.booking_date == date(2026, 5, 18), errors.append("html: booking_date")
    assert result.listing_id == "HTL54321:RM5678", errors.append("html: listing_id")
    assert result.needs_manual_review is False, errors.append("html: needs_manual_review")
    assert result.overall_confidence >= 0.8, errors.append("html: overall_confidence")

    # --- Test missing fields ---
    raw = _make_raw_email(body_text="Hello from MakeMyTrip. No booking details here.")
    result = parser.parse(raw)
    assert result.ota_reference_id is None, errors.append("missing: ota_reference_id")
    assert result.check_in is None, errors.append("missing: check_in")
    assert result.check_out is None, errors.append("missing: check_out")
    assert result.gross_amount is None, errors.append("missing: gross_amount")
    assert result.overall_confidence < 0.8, errors.append("missing: overall_confidence")
    assert result.needs_manual_review is True, errors.append("missing: needs_manual_review")
    assert result.review_reason is not None, errors.append("missing: review_reason")

    # --- Test partial fields ---
    body = (
        "Booking Reference: BRN999\n"
        "Check-in Date: 01 Jun 2026\n"
        "Check-out Date: 03 Jun 2026\n"
    )
    raw = _make_raw_email(body_text=body)
    result = parser.parse(raw)
    assert result.ota_reference_id == "BRN999", errors.append("partial: ota_reference_id")
    assert result.check_in == date(2026, 6, 1), errors.append("partial: check_in")
    assert result.check_out == date(2026, 6, 3), errors.append("partial: check_out")
    assert result.needs_manual_review is True, errors.append("partial: needs_manual_review")

    # --- Test HTML + text fallback ---
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
    assert result.ota_reference_id == "BRN777", errors.append("fallback: ota_reference_id")
    assert result.check_in == date(2026, 6, 5), errors.append("fallback: check_in")
    assert result.check_out == date(2026, 6, 7), errors.append("fallback: check_out")
    assert result.guest_name == "Amit Singh", errors.append("fallback: guest_name")
    assert result.gross_amount == 5000.00, errors.append("fallback: gross_amount")

    # --- Test listing_id fallback to names ---
    body = "Hotel Name: Ocean View\nRoom Type Name: Suite\n"
    raw = _make_raw_email(body_text=body)
    result = parser.parse(raw)
    assert result.listing_id == "Ocean View|Suite", errors.append("fallback_names: listing_id")

    # --- Test guest count variants ---
    raw = _make_raw_email(body_text="Guests: 2 Adults")
    result = parser.parse(raw)
    assert result.number_of_guests == 2, errors.append("guests: 2 Adults")

    raw = _make_raw_email(body_text="Guests: 3 Adults, 2 Children")
    result = parser.parse(raw)
    assert result.number_of_guests == 5, errors.append("guests: 3 Adults, 2 Children")

    # --- Test date variants ---
    for variant in ["15 May 2026", "15-May-2026", "15/05/2026", "2026-05-15"]:
        raw = _make_raw_email(body_text=f"Check-in Date: {variant}")
        result = parser.parse(raw)
        assert result.check_in == date(2026, 5, 15), f"date variant failed: {variant}"

    # --- Test amount variants ---
    for raw_val, expected in [("INR 12,500.00", 12500.00), ("Rs. 8400", 8400.00), ("₹1,260.00", 1260.00), ("2500", 2500.00)]:
        raw = _make_raw_email(body_text=f"Total Amount: {raw_val}")
        result = parser.parse(raw)
        assert result.gross_amount == expected, f"amount variant failed: {raw_val}"

    if errors:
        print(f"FAILED with {len(errors)} errors:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("All standalone MMT parser tests passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
