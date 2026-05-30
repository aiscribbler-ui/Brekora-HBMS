"""Airbnb reservation confirmation email parser.

Uses regex + structured text extraction (no ML) to extract booking fields
from both plain-text and HTML Airbnb confirmation emails.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from html.parser import HTMLParser
from typing import Any

from app.models.raw_email import RawEmail

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONFIRMATION_CODE_RE = re.compile(
    r"(?:Confirmation|Reservation|Booking)\s+(?:code|#|number|ID)[:\s#]*([A-Z0-9]{6,12})",
    re.IGNORECASE,
)

# Primary: labels that clearly indicate the guest (NOT the host or property)
GUEST_NAME_RE = re.compile(
    r"(?:Guest|Booked by)[:\s]*\n?\s*([A-Z][a-z]+(?:\s[A-Z][a-z]+){0,3})",
    re.IGNORECASE | re.MULTILINE,
)

# Airbnb thread format: the guest name appears twice on its own line before "Booker"
# e.g.  Vi\nVi\nBooker
GUEST_THREAD_RE = re.compile(
    r"(?:^|\n)\s*([A-Z][a-z]+)\s*(?:\n\s*\1\s*)?\n\s*Booker",
    re.IGNORECASE | re.MULTILINE,
)

# Guest self-introduction: "I'm Vi from Vietnam"
GUEST_INTRO_RE = re.compile(
    r"\bI['']?m\s+([A-Z][a-z]+)\s+from\b",
    re.IGNORECASE,
)

# Guard: reject host names that sometimes slip through
HOST_LABEL_RE = re.compile(
    r"(?:Hosted by|Host)[:\s]*\n?\s*([A-Z][a-z]+(?:\s[A-Z][a-z]+){0,3})",
    re.IGNORECASE | re.MULTILINE,
)

GUEST_EMAIL_RE = re.compile(
    r"(?:Guest email|Email|Contact email)[:\s]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
    re.IGNORECASE,
)

# Flexible date patterns used by Airbnb (English + common variants)
_DATE_PATTERNS = [
    # "Sunday, April 27, 2025" or "Sun, Apr 27, 2025"
    re.compile(
        r"(?:(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*,?\s+)?"
        r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*)\s+"
        r"(\d{1,2}),?\s+(\d{4})",
        re.IGNORECASE,
    ),
    # "27 April 2025" or "27 Apr 2025"
    re.compile(
        r"(\d{1,2})\s+((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*)\s+(\d{4})",
        re.IGNORECASE,
    ),
    # "2025-04-27"
    re.compile(r"(\d{4})-(\d{2})-(\d{2})"),
    # "04/27/2025"
    re.compile(r"(\d{2})/(\d{2})/(\d{4})"),
]

_CHECK_IN_LABELS = re.compile(
    r"\b(?:Check[\s\-]?in|Arrival|Arrive)\b[:\s]*", re.IGNORECASE
)
_CHECK_OUT_LABELS = re.compile(
    r"\b(?:Check[\s\-]?out|Departure|Depart|Until)\b[:\s]*", re.IGNORECASE
)

_NUMBER_OF_GUESTS_RE = re.compile(
    r"(?<!\w)(\d+)\s+(?:guest|adult|traveler)s?", re.IGNORECASE
)

_LISTING_ID_RE = re.compile(
    r"(?:Listing\s*ID|Property\s*ID|Listing\s*#)[:\s#]*(\d+)", re.IGNORECASE
)

_PROPERTY_NAME_RE = re.compile(
    r"(?:Listing|Property| Accommodation)[:\s]*\n?\s*([^\n]{3,80})",
    re.IGNORECASE | re.MULTILINE,
)

# Amount patterns — support INR ₹, USD $, EUR €, GBP £, etc.
# Uses a non-greedy "skip" up to 40 chars (not digit/currency) so that
# "Total (INR) ₹12,000" and "Total\n₹12,000" both match.
_AMOUNT_RE = re.compile(
    r"(?:Total|Gross|Subtotal|Amount)" r"[^₹$€£\d]{0,40}?" r"([₹$€£]\s*[\d,]+\.?\d*)",
    re.IGNORECASE,
)

_COMMISSION_RE = re.compile(
    r"(?:Airbnb\s*service\s*fee|Service\s*fee|Commission|OTA\s*fee|Platform\s*fee)"
    r"[^₹$€£\d\-]{0,40}?"
    r"(-?\s*[₹$€£]\s*[\d,]+\.?\d*)",
    re.IGNORECASE,
)

_PAYOUT_RE = re.compile(
    r"(?:You\s*earn|Host\s*payout|Payout|Net\s*amount|Your\s*earnings)"
    r"[^₹$€£\d]{0,40}?"
    r"([₹$€£]\s*[\d,]+\.?\d*)",
    re.IGNORECASE,
)

_BOOKING_DATE_RE = re.compile(
    r"(?:Booked on|Reservation made|Booking date|Reserved on)[:\s]*"
    r"([A-Za-z]+\s+\d{1,2},?\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})",
    re.IGNORECASE,
)

_SPECIAL_REQUESTS_RE = re.compile(
    r"(?:Special\s*requests?|Notes?|Message\s*from\s*guest|Guest\s*message)[:\s]*\n?\s*([^\n]{5,500})",
    re.IGNORECASE | re.MULTILINE,
)

_MONTH_MAP = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


# ---------------------------------------------------------------------------
# HTML stripper
# ---------------------------------------------------------------------------

class _HTMLStripper(HTMLParser):
    """Minimal std-lib HTML tag stripper that preserves block-level whitespace."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text_parts: list[str] = []
        self._last_tag: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._last_tag = tag.lower()
        if tag.lower() in ("br", "p", "div", "li", "tr", "td", "h1", "h2", "h3", "h4"):
            self.text_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in ("p", "div", "li", "tr", "td", "h1", "h2", "h3", "h4"):
            self.text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.text_parts.append(data)

    def get_text(self) -> str:
        text = "".join(self.text_parts)
        # Collapse multiple blank lines to make regex life easier
        return re.sub(r"\n{3,}", "\n\n", text)


def _strip_html(html: str) -> str:
    stripper = _HTMLStripper()
    try:
        stripper.feed(html)
    except Exception as exc:
        logger.warning("HTML stripper failed, falling back to regex: %s", exc)
        # Fallback: naive tag removal
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s{2,}", " ", text)
        return text.strip()
    return stripper.get_text().strip()


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _parse_date(text: str) -> date | None:
    """Try to extract a date from a string fragment."""
    for pat in _DATE_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        groups = m.groups()
        try:
            if len(groups) == 3:
                # Check if first group is a 4-digit year (ISO format)
                if groups[0].startswith("20") and len(groups[0]) == 4:
                    # ISO: 2025-04-27
                    return date(int(groups[0]), int(groups[1]), int(groups[2]))
                # Check if first group is a 2-digit number (slash format)
                if groups[0].isdigit() and len(groups[0]) == 2:
                    # Slash: 04/27/2025 (US style) — Airbnb rarely uses this but handle it
                    return date(int(groups[2]), int(groups[0]), int(groups[1]))
                # Textual month format — first group is month word
                month_str = groups[0][:3].lower()
                month = _MONTH_MAP.get(month_str)
                if month is None:
                    continue
                day = int(groups[1])
                year = int(groups[2])
                return date(year, month, day)
        except (ValueError, IndexError):
            continue

    # Generic fallback: "27 Apr 2025" with month in the middle
    m = re.search(
        r"(\d{1,2})\s+([A-Za-z]{3,})\s+(\d{4})", text, re.IGNORECASE
    )
    if m:
        day = int(m.group(1))
        month_str = m.group(2)[:3].lower()
        month = _MONTH_MAP.get(month_str)
        year = int(m.group(3))
        if month:
            try:
                return date(year, month, day)
            except ValueError:
                pass

    # ISO fallback
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    return None


def _parse_amount(text: str) -> Decimal | None:
    """Parse a monetary amount string like '₹12,000.00' or '$1,234.56'."""
    if not text:
        return None
    # Remove currency symbols and commas, keep dot
    cleaned = re.sub(r"[^\d.-]", "", text)
    try:
        return Decimal(cleaned) if cleaned else None
    except Exception:
        return None


def _extract_after_label(text: str, label_re: re.Pattern, window: int = 200) -> str:
    """Return the text window immediately following the first match of label_re."""
    m = label_re.search(text)
    if not m:
        return ""
    start = m.end()
    return text[start : start + window]


def _extract_date_after_label(text: str, label_re: re.Pattern) -> date | None:
    """Find a label and parse the first date that appears within 150 chars after it."""
    window = _extract_after_label(text, label_re, 150)
    return _parse_date(window)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ParsedField:
    """Single extracted field with confidence."""

    value: Any
    confidence: float = 0.0
    source_snippet: str = ""


@dataclass
class ParsedBookingResult:
    """Normalized result from parsing an OTA confirmation email.

    This is the intermediate format produced by parsers.  It will later be
    mapped to the canonical ``CanonicalBooking`` schema defined by Agent B.
    """

    ota_source: str = "airbnb"
    ota_reference_id: str | None = None
    guest_name: str | None = None
    guest_email: str | None = None
    check_in: date | None = None
    check_out: date | None = None
    room_type: str | None = None
    listing_id: str | None = None
    number_of_guests: int | None = None
    gross_amount: Decimal | None = None
    ota_commission: Decimal | None = None
    net_payout: Decimal | None = None
    special_requests: str | None = None
    booking_date: date | None = None
    field_confidences: dict[str, float] = field(default_factory=dict)
    overall_confidence: float = 0.0
    needs_review: bool = False
    review_reason: str = ""
    raw_snippets: dict[str, str] = field(default_factory=dict)

    def to_canonical_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serializable dict for downstream processing."""
        return {
            "ota_source": self.ota_source,
            "ota_reference_id": self.ota_reference_id,
            "guest_name": self.guest_name,
            "guest_email": self.guest_email,
            "check_in": self.check_in.isoformat() if self.check_in else None,
            "check_out": self.check_out.isoformat() if self.check_out else None,
            "room_type": self.room_type,
            "listing_id": self.listing_id,
            "number_of_guests": self.number_of_guests,
            "gross_amount": str(self.gross_amount) if self.gross_amount is not None else None,
            "ota_commission": str(self.ota_commission) if self.ota_commission is not None else None,
            "net_payout": str(self.net_payout) if self.net_payout is not None else None,
            "special_requests": self.special_requests,
            "booking_date": self.booking_date.isoformat() if self.booking_date else None,
            "overall_confidence": self.overall_confidence,
            "needs_review": self.needs_review,
            "review_reason": self.review_reason,
            "field_confidences": self.field_confidences,
        }


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class AirbnbParser:
    """Extract structured booking data from Airbnb reservation confirmation emails."""

    # Fields considered *critical* for a valid booking. Missing these lowers
    # confidence more aggressively.
    CRITICAL_FIELDS: tuple[str, ...] = (
        "ota_reference_id",
        "check_in",
        "check_out",
        "gross_amount",
        "net_payout",
    )

    def parse(self, raw_email: RawEmail) -> ParsedBookingResult:
        """Parse an Airbnb raw email into a structured booking result.

        Args:
            raw_email: The ``RawEmail`` DB model instance.

        Returns:
            ``ParsedBookingResult`` with confidence scores and review flag.
        """
        # Choose best text source
        text = self._get_primary_text(raw_email)
        if not text:
            logger.warning(
                "AirbnbParser: no parseable text for raw_email id=%s", raw_email.id
            )
            return ParsedBookingResult(
                needs_review=True,
                review_reason="No parseable text content found.",
            )

        # Normalize whitespace for regex stability
        text = re.sub(r"\t+", " ", text)
        text = re.sub(r" {2,}", " ", text)

        result = ParsedBookingResult(ota_source="airbnb")

        # Detect email subtype so we can adjust critical fields / weights
        email_subtype = self._detect_email_subtype(text)

        # --- Individual field extraction ------------------------------------

        result.ota_reference_id, result.field_confidences["ota_reference_id"] = (
            self._extract_confirmation_code(text)
        )
        result.guest_name, result.field_confidences["guest_name"] = (
            self._extract_guest_name(text)
        )
        result.guest_email, result.field_confidences["guest_email"] = (
            self._extract_guest_email(text)
        )
        result.check_in, result.field_confidences["check_in"] = self._extract_check_in(
            text
        )
        result.check_out, result.field_confidences["check_out"] = self._extract_check_out(
            text
        )
        result.listing_id, result.field_confidences["listing_id"] = self._extract_listing_id(
            text
        )
        result.room_type, result.field_confidences["room_type"] = self._extract_room_type(
            text, result.listing_id
        )
        result.number_of_guests, result.field_confidences["number_of_guests"] = (
            self._extract_guest_count(text)
        )
        result.gross_amount, result.field_confidences["gross_amount"] = (
            self._extract_gross_amount(text)
        )
        result.ota_commission, result.field_confidences["ota_commission"] = (
            self._extract_commission(text)
        )
        result.net_payout, result.field_confidences["net_payout"] = self._extract_payout(
            text
        )
        result.special_requests, result.field_confidences["special_requests"] = (
            self._extract_special_requests(text)
        )
        result.booking_date, result.field_confidences["booking_date"] = (
            self._extract_booking_date(text)
        )

        # --- Confidence aggregation ------------------------------------------

        result.overall_confidence = self._compute_overall_confidence(result, email_subtype)
        result.needs_review = result.overall_confidence < 0.8

        if result.needs_review:
            critical = self._critical_fields_for_subtype(email_subtype)
            missing = [
                f
                for f in critical
                if result.field_confidences.get(f, 0.0) == 0.0
            ]
            if missing:
                result.review_reason = (
                    f"Low confidence ({result.overall_confidence:.2f}). "
                    f"Missing critical fields: {', '.join(missing)}."
                )
            else:
                result.review_reason = (
                    f"Low overall confidence ({result.overall_confidence:.2f}). "
                    f"Some extracted fields may be unreliable."
                )

        # Store short snippets for debugging / audit
        result.raw_snippets = {
            "confirmation_code": result.ota_reference_id or "",
            "guest": result.guest_name or "",
            "dates": f"{result.check_in} → {result.check_out}",
            "amounts": f"gross={result.gross_amount} commission={result.ota_commission} payout={result.net_payout}",
        }

        logger.info(
            "AirbnbParser: parsed email id=%s confidence=%.2f needs_review=%s",
            raw_email.id,
            result.overall_confidence,
            result.needs_review,
        )
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_email_subtype(text: str) -> str:
        """Detect whether this is a full confirmation or an initial notification."""
        has_code = bool(CONFIRMATION_CODE_RE.search(text))
        has_amount = bool(_AMOUNT_RE.search(text))
        has_payout = bool(_PAYOUT_RE.search(text))
        looks_like_notification = bool(
            re.search(r"Reservation\s+for", text, re.IGNORECASE)
        )
        if has_code and has_amount and has_payout:
            return "confirmation"
        if looks_like_notification and not has_code:
            return "notification"
        return "unknown"

    @staticmethod
    def _critical_fields_for_subtype(subtype: str) -> tuple[str, ...]:
        if subtype == "notification":
            # Initial reservation emails often lack code + pricing
            return ("check_in", "check_out", "guest_name", "number_of_guests")
        return ("ota_reference_id", "check_in", "check_out", "gross_amount", "net_payout")

    @staticmethod
    def _get_primary_text(raw_email: RawEmail) -> str:
        """Return plain text for parsing, stripping HTML if necessary."""
        if raw_email.body_text:
            return raw_email.body_text
        if raw_email.body_html:
            return _strip_html(raw_email.body_html)
        return ""

    @staticmethod
    def _extract_confirmation_code(text: str) -> tuple[str | None, float]:
        m = CONFIRMATION_CODE_RE.search(text)
        if m:
            code = m.group(1).strip().upper()
            return code, 1.0
        return None, 0.0

    @staticmethod
    def _extract_guest_name(text: str) -> tuple[str | None, float]:
        # 1. Airbnb thread format: Name\nName\nBooker  (highest confidence)
        m = GUEST_THREAD_RE.search(text)
        if m:
            name = m.group(1).strip()
            if len(name) > 1:
                return name, 1.0

        # 2. Guest self-intro: "I'm Vi from Vietnam"
        m = GUEST_INTRO_RE.search(text)
        if m:
            name = m.group(1).strip()
            if len(name) > 1:
                return name, 0.95

        # 3. Explicit guest labels
        m = GUEST_NAME_RE.search(text)
        if m:
            name = m.group(1).strip()
            if len(name) > 2 and not name.isdigit():
                return name, 0.9

        # Guard: make sure we didn't accidentally extract the host name
        host_match = HOST_LABEL_RE.search(text)
        if host_match:
            host_name = host_match.group(1).strip().lower()
        else:
            host_name = None

        # Fallback: look for a line that starts with a capitalised name near the word "guest"
        fallback = re.search(
            r"(?:^|\n)\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\s*\n?\s*(?:guest|traveller)",
            text,
            re.IGNORECASE | re.MULTILINE,
        )
        if fallback:
            name = fallback.group(1).strip()
            if host_name and name.lower() == host_name:
                return None, 0.0
            return name, 0.75
        return None, 0.0

    @staticmethod
    def _extract_guest_email(text: str) -> tuple[str | None, float]:
        m = GUEST_EMAIL_RE.search(text)
        if m:
            return m.group(1).strip().lower(), 1.0
        # Fallback: generic email regex anywhere in body
        fallback = re.search(
            r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", text
        )
        if fallback:
            email = fallback.group(1).lower()
            # Avoid matching generic Airbnb domains
            if "airbnb" not in email and "no-reply" not in email:
                return email, 0.6
        return None, 0.0

    @staticmethod
    def _extract_check_in(text: str) -> tuple[date | None, float]:
        dt = _extract_date_after_label(text, _CHECK_IN_LABELS)
        if dt:
            return dt, 0.95
        # Fallback: first plausible date in the email
        dt = _parse_date(text)
        if dt:
            return dt, 0.6
        return None, 0.0

    @staticmethod
    def _extract_check_out(text: str) -> tuple[date | None, float]:
        dt = _extract_date_after_label(text, _CHECK_OUT_LABELS)
        if dt:
            return dt, 0.95
        # Fallback: try to find a second date after the first one
        first_date = _extract_date_after_label(text, _CHECK_IN_LABELS)
        if first_date:
            # Remove the first date string from a copy and search again
            snippet = text
            for pat in _DATE_PATTERNS:
                m = pat.search(snippet)
                if m:
                    snippet = snippet[m.end() :]
                    break
            second = _parse_date(snippet)
            if second and second != first_date:
                return second, 0.7
        return None, 0.0

    @staticmethod
    def _extract_listing_id(text: str) -> tuple[str | None, float]:
        m = _LISTING_ID_RE.search(text)
        if m:
            return m.group(1).strip(), 1.0
        # Fallback: look for any 8-10 digit number that might be a listing ID
        fallback = re.search(r"(?<!\d)(\d{8,10})(?!\d)", text)
        if fallback:
            return fallback.group(1), 0.5
        return None, 0.0

    @staticmethod
    def _extract_room_type(text: str, listing_id: str | None) -> tuple[str | None, float]:
        m = _PROPERTY_NAME_RE.search(text)
        if m:
            name = m.group(1).strip()
            if name and len(name) > 2:
                return name, 0.9
        # Fallback: use listing_id as room_type hint if nothing else found
        if listing_id:
            return None, 0.3
        return None, 0.0

    @staticmethod
    def _extract_guest_count(text: str) -> tuple[int | None, float]:
        m = _NUMBER_OF_GUESTS_RE.search(text)
        if m:
            return int(m.group(1)), 0.95
        return None, 0.0

    @staticmethod
    def _extract_gross_amount(text: str) -> tuple[Decimal | None, float]:
        m = _AMOUNT_RE.search(text)
        if m:
            return _parse_amount(m.group(1)), 0.9
        # Fallback: largest currency-looking number in the email
        fallback = re.findall(r"[₹$€£]\s*([\d,]+\.?\d*)", text)
        if fallback:
            values = [Decimal(re.sub(r",", "", v)) for v in fallback]
            if values:
                return max(values), 0.6
        return None, 0.0

    @staticmethod
    def _extract_commission(text: str) -> tuple[Decimal | None, float]:
        m = _COMMISSION_RE.search(text)
        if m:
            amount = _parse_amount(m.group(1))
            if amount is not None:
                return abs(amount), 0.9
        return None, 0.0

    @staticmethod
    def _extract_payout(text: str) -> tuple[Decimal | None, float]:
        m = _PAYOUT_RE.search(text)
        if m:
            return _parse_amount(m.group(1)), 0.95
        # Fallback: if gross and commission are present, compute net
        gross_match = _AMOUNT_RE.search(text)
        comm_match = _COMMISSION_RE.search(text)
        if gross_match and comm_match:
            gross = _parse_amount(gross_match.group(1))
            comm = _parse_amount(comm_match.group(1))
            if gross is not None and comm is not None:
                return gross - comm, 0.7
        return None, 0.0

    @staticmethod
    def _extract_special_requests(text: str) -> tuple[str | None, float]:
        m = _SPECIAL_REQUESTS_RE.search(text)
        if m:
            req = m.group(1).strip()
            if len(req) > 5:
                return req, 0.85
        return None, 0.0

    @staticmethod
    def _extract_booking_date(text: str) -> tuple[date | None, float]:
        m = _BOOKING_DATE_RE.search(text)
        if m:
            dt = _parse_date(m.group(1))
            if dt:
                return dt, 0.95
        return None, 0.0

    def _compute_overall_confidence(
        self, result: ParsedBookingResult, subtype: str = "unknown"
    ) -> float:
        """Compute weighted overall confidence score.

        Critical fields are weighted 2x; nice-to-have fields are weighted 1x.
        Missing commission is less severe than missing confirmation code.
        For ``notification`` subtypes (initial reservation emails without code
        or pricing) we lower the weight of code/price so the score reflects
        the fields that are actually present.
        """
        if subtype == "notification":
            weights: dict[str, float] = {
                "ota_reference_id": 1.0,
                "check_in": 2.5,
                "check_out": 2.5,
                "gross_amount": 0.5,
                "net_payout": 0.5,
                "guest_name": 2.0,
                "number_of_guests": 2.0,
                "listing_id": 1.0,
                "room_type": 1.0,
                "booking_date": 1.0,
                "ota_commission": 0.5,
                "guest_email": 0.5,
                "special_requests": 0.5,
            }
        else:
            weights = {
                "ota_reference_id": 3.0,
                "check_in": 2.5,
                "check_out": 2.5,
                "gross_amount": 2.0,
                "net_payout": 2.0,
                "guest_name": 1.5,
                "number_of_guests": 1.5,
                "listing_id": 1.0,
                "room_type": 1.0,
                "booking_date": 1.0,
                "ota_commission": 1.0,
                "guest_email": 0.5,
                "special_requests": 0.5,
            }
        total_weight = 0.0
        weighted_sum = 0.0
        for field_name, weight in weights.items():
            conf = result.field_confidences.get(field_name, 0.0)
            weighted_sum += conf * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        return round(weighted_sum / total_weight, 3)
