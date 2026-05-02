import logging
from datetime import date, datetime
from typing import Any

import httpx
from icalendar import Calendar

logger = logging.getLogger(__name__)


class IcalService:
    """Fetch and parse iCal feeds into plain dicts."""

    @staticmethod
    async def fetch_and_parse(feed_url: str) -> list[dict[str, Any]]:
        """Download an iCal feed and return a list of VEVENT dicts."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(feed_url)
            response.raise_for_status()
            content = response.text
        return IcalService.parse_ical(content, feed_url)

    @staticmethod
    def parse_ical(ical_data: str, feed_url: str = "") -> list[dict[str, Any]]:
        """Parse an iCal string and extract VEVENT fields."""
        cal = Calendar.from_ical(ical_data)
        events: list[dict[str, Any]] = []
        for component in cal.walk():
            if component.name != "VEVENT":
                continue
            dtstart = component.get("dtstart")
            dtend = component.get("dtend")
            events.append(
                {
                    "uid": str(component.get("uid", "")),
                    "summary": str(component.get("summary", "")),
                    "dtstart": IcalService._to_date(dtstart),
                    "dtend": IcalService._to_date(dtend),
                    "description": str(component.get("description", "")),
                    "feed_url": feed_url,
                }
            )
        return events

    @staticmethod
    def _to_date(dt: Any) -> date | None:
        """Convert an icalendar date/datetime property to a Python date."""
        if dt is None:
            return None
        val = getattr(dt, "dt", dt)
        if isinstance(val, datetime):
            return val.date()
        if isinstance(val, date):
            return val
        return None

    @staticmethod
    def dedup(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove events with duplicate UIDs, keeping the first occurrence."""
        seen: set[str] = set()
        result: list[dict[str, Any]] = []
        for event in events:
            uid = event.get("uid")
            if uid and uid in seen:
                continue
            if uid:
                seen.add(uid)
            result.append(event)
        return result
