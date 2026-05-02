"""Tests for iCal parser and ICalSource adapter."""
import uuid
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.services.channels.ical_source import ICalSource
from app.services.ical_service import IcalService


SAMPLE_ICS = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Brekora BMS//Test iCal//EN
BEGIN:VEVENT
UID:test-event-1@brekora.local
SUMMARY:Booking for Alice
DTSTART;VALUE=DATE:20260601
DTEND;VALUE=DATE:20260603
DESCRIPTION:Guest Alice, 2 guests
END:VEVENT
BEGIN:VEVENT
UID:test-event-2@brekora.local
SUMMARY:Booking for Bob
DTSTART;VALUE=DATE:20260610
DTEND;VALUE=DATE:20260612
DESCRIPTION:Guest Bob, 1 guest
END:VEVENT
END:VCALENDAR
"""


def test_parse_ical():
    events = IcalService.parse_ical(SAMPLE_ICS, feed_url="http://example.com/cal.ics")
    assert len(events) == 2
    assert events[0]["uid"] == "test-event-1@brekora.local"
    assert events[0]["summary"] == "Booking for Alice"
    assert events[0]["dtstart"] == date(2026, 6, 1)
    assert events[0]["dtend"] == date(2026, 6, 3)
    assert events[0]["description"] == "Guest Alice, 2 guests"
    assert events[0]["feed_url"] == "http://example.com/cal.ics"

    assert events[1]["uid"] == "test-event-2@brekora.local"
    assert events[1]["summary"] == "Booking for Bob"
    assert events[1]["dtstart"] == date(2026, 6, 10)
    assert events[1]["dtend"] == date(2026, 6, 12)


def test_dedup_by_uid():
    events = [
        {"uid": "a", "summary": "First"},
        {"uid": "a", "summary": "Duplicate"},
        {"uid": "b", "summary": "Second"},
        {"uid": "", "summary": "No uid"},
    ]
    result = IcalService.dedup(events)
    assert len(result) == 3
    assert result[0]["summary"] == "First"
    assert result[1]["summary"] == "Second"
    assert result[2]["summary"] == "No uid"


@pytest.mark.asyncio
async def test_normalize_with_mock_feed_url():
    source = ICalSource()
    mock_events = [
        {
            "uid": "evt-1",
            "summary": "Mock Booking",
            "dtstart": date(2026, 7, 1),
            "dtend": date(2026, 7, 5),
            "description": "Mock desc",
            "feed_url": "http://example.com/cal.ics",
        }
    ]

    with patch(
        "app.services.channels.ical_source.IcalService.fetch_and_parse",
        new_callable=AsyncMock,
        return_value=mock_events,
    ):
        with patch(
            "app.services.channels.ical_source.IcalService.dedup",
            return_value=mock_events,
        ):
            raw_payload = {
                "feed_url": "http://example.com/cal.ics",
                "uid": "evt-1",
                "gross_amount": 100,
                "currency": "USD",
            }
            booking = await source.normalize(raw_payload)

    assert booking.source_type == "ical"
    assert booking.source_reference == "evt-1"
    assert booking.check_in == date(2026, 7, 1)
    assert booking.check_out == date(2026, 7, 5)
    assert booking.guest_name == "Mock Booking"
    assert booking.special_requests == "Mock desc"
    assert booking.gross_amount == 100
    assert booking.currency == "USD"


@pytest.mark.asyncio
async def test_normalize_fallback_without_feed_url():
    source = ICalSource()
    raw_payload = {
        "uid": "local-uid",
        "summary": "Local Booking",
        "dtstart": date(2026, 8, 1),
        "dtend": date(2026, 8, 3),
        "property_id": uuid.uuid4(),
        "room_type_id": uuid.uuid4(),
    }
    booking = await source.normalize(raw_payload)
    assert booking.source_reference == "local-uid"
    assert booking.guest_name == "Local Booking"
    assert booking.check_in == date(2026, 8, 1)
    assert booking.check_out == date(2026, 8, 3)
    assert booking.metadata.get("feed_url") is None
