"""MakeMyTrip (MMT) booking voucher email parser."""
import re
from datetime import date, datetime
from typing import Any, Optional

from bs4 import BeautifulSoup

from app.models.raw_email import RawEmail
from app.schemas.parsed_booking import ParsedBookingResult


class MMTParser:
    """Parse MakeMyTrip booking voucher emails into structured booking data."""

    # Regex patterns for text extraction
    _RE_PATTERNS: dict[str, list[re.Pattern]] = {
        "voucher_number": [
            re.compile(r"Voucher\s*(?:Number|No\.?|#)\s*[:\-]?\s*([A-Z0-9]+)", re.IGNORECASE),
            re.compile(r"Voucher\s*ID\s*[:\-]?\s*([A-Z0-9]+)", re.IGNORECASE),
        ],
        "ota_reference_id": [
            re.compile(r"Booking\s*Reference\s*(?:Number|No\.?|#)?\s*[:\-]?\s*([A-Z0-9]+)", re.IGNORECASE),
            re.compile(r"Reference\s*(?:Number|No\.?|#)?\s*[:\-]?\s*([A-Z0-9]+)", re.IGNORECASE),
            re.compile(r"Booking\s*ID\s*[:\-]?\s*([A-Z0-9]+)", re.IGNORECASE),
        ],
        "hotel_name": [
            re.compile(r"Hotel\s*Name\s*[:\-]?\s*(.+?)(?:\n|\r|$)", re.IGNORECASE),
            re.compile(r"Property\s*Name\s*[:\-]?\s*(.+?)(?:\n|\r|$)", re.IGNORECASE),
        ],
        "hotel_code": [
            re.compile(r"Hotel\s*Code\s*[:\-]?\s*([A-Z0-9]+)", re.IGNORECASE),
        ],
        "room_type_name": [
            re.compile(r"Room\s*Type\s*Name\s*[:\-]?\s*(.+?)(?:\n|\r|$)", re.IGNORECASE),
            re.compile(r"Room\s*Type\s*[:\-]?\s*(.+?)(?:\n|\r|$)", re.IGNORECASE),
        ],
        "room_code": [
            re.compile(r"Room\s*Code\s*[:\-]?\s*([A-Z0-9]+)", re.IGNORECASE),
        ],
        "guest_name": [
            re.compile(r"Guest\s*Name\s*[:\-]?\s*(.+?)(?:\n|\r|$)", re.IGNORECASE),
            re.compile(r"Primary\s*Guest\s*[:\-]?\s*(.+?)(?:\n|\r|$)", re.IGNORECASE),
            re.compile(r"Booked\s*By\s*[:\-]?\s*(.+?)(?:\n|\r|$)", re.IGNORECASE),
        ],
        "guest_email": [
            re.compile(r"Guest\s*Email\s*[:\-]?\s*([\w.+-]+@[\w.-]+\.[A-Za-z]{2,})", re.IGNORECASE),
            re.compile(r"Email\s*[:\-]?\s*([\w.+-]+@[\w.-]+\.[A-Za-z]{2,})", re.IGNORECASE),
        ],
        "check_in": [
            re.compile(r"Check[-\s]?in\s*(?:Date)?\s*[:\-]?\s*(.+?)(?:\n|\r|$)", re.IGNORECASE),
            re.compile(r"Arrival\s*(?:Date)?\s*[:\-]?\s*(.+?)(?:\n|\r|$)", re.IGNORECASE),
        ],
        "check_out": [
            re.compile(r"Check[-\s]?out\s*(?:Date)?\s*[:\-]?\s*(.+?)(?:\n|\r|$)", re.IGNORECASE),
            re.compile(r"Departure\s*(?:Date)?\s*[:\-]?\s*(.+?)(?:\n|\r|$)", re.IGNORECASE),
        ],
        "number_of_rooms": [
            re.compile(r"Number\s*of\s*Rooms\s*[:\-]?\s*(\d+)", re.IGNORECASE),
            re.compile(r"Rooms\s*[:\-]?\s*(\d+)", re.IGNORECASE),
        ],
        "number_of_guests": [
            re.compile(r"Guests?\s*[:\-]?\s*(.+?)(?:\n|\r|$)", re.IGNORECASE),
            re.compile(r"Occupancy\s*[:\-]?\s*(.+?)(?:\n|\r|$)", re.IGNORECASE),
            re.compile(r"(\d+)\s*(?:Adults?|Guests?)", re.IGNORECASE),
        ],
        "gross_amount": [
            re.compile(r"Total\s*Amount\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+\.?\d*)", re.IGNORECASE),
            re.compile(r"Gross\s*Amount\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+\.?\d*)", re.IGNORECASE),
            re.compile(r"Amount\s*Paid\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+\.?\d*)", re.IGNORECASE),
        ],
        "ota_commission": [
            re.compile(r"(?:OTA\s*)?Commission\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+\.?\d*)", re.IGNORECASE),
            re.compile(r"Commission\s*Fee\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+\.?\d*)", re.IGNORECASE),
        ],
        "net_payout": [
            re.compile(r"Net\s*(?:Payable|Payout)\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+\.?\d*)", re.IGNORECASE),
            re.compile(r"You\s*Receive\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+\.?\d*)", re.IGNORECASE),
        ],
        "special_requests": [
            re.compile(r"Special\s*Requests?\s*[:\-]?\s*(.+?)(?:\n\n|\r\r|$)", re.IGNORECASE | re.DOTALL),
        ],
        "booking_date": [
            re.compile(r"Booking\s*Date\s*[:\-]?\s*(.+?)(?:\n|\r|$)", re.IGNORECASE),
            re.compile(r"Booked\s*On\s*[:\-]?\s*(.+?)(?:\n|\r|$)", re.IGNORECASE),
        ],
    }

    _DATE_FORMATS = [
        "%d %b %Y",
        "%d %B %Y",
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%b %d, %Y",
        "%B %d, %Y",
    ]

    def parse(self, raw_email: RawEmail) -> ParsedBookingResult:
        """Parse a raw MMT email into a ParsedBookingResult."""
        text_body = raw_email.body_text or ""
        html_body = raw_email.body_html or ""

        data: dict[str, Any] = {}
        confidence: dict[str, float] = {}

        # Prefer HTML tables first, fallback to text
        if html_body.strip():
            html_data, html_conf = self._extract_from_html(html_body)
            data.update(html_data)
            confidence.update(html_conf)

        # Text extraction fills anything missing or overrides with higher confidence
        text_data, text_conf = self._extract_from_text(text_body)
        for key, val in text_data.items():
            if val is not None and (data.get(key) is None or text_conf.get(key, 0) > confidence.get(key, 0)):
                data[key] = val
                confidence[key] = text_conf.get(key, 0.5)

        # Build result
        result_data = {
            "ota_reference_id": data.get("ota_reference_id"),
            "guest_name": data.get("guest_name"),
            "guest_email": data.get("guest_email"),
            "check_in": data.get("check_in"),
            "check_out": data.get("check_out"),
            "listing_id": self._build_listing_id(data),
            "number_of_guests": data.get("number_of_guests"),
            "gross_amount": data.get("gross_amount"),
            "ota_commission": data.get("ota_commission"),
            "net_payout": data.get("net_payout"),
            "special_requests": data.get("special_requests"),
            "booking_date": data.get("booking_date"),
            "voucher_number": data.get("voucher_number"),
            "hotel_name": data.get("hotel_name"),
            "room_type_name": data.get("room_type_name"),
            "number_of_rooms": data.get("number_of_rooms"),
            "confidence_scores": confidence,
            "overall_confidence": 0.0,
            "needs_manual_review": False,
            "review_reason": None,
            "raw_payload": {
                "subject": raw_email.subject,
                "sender": raw_email.sender,
                "body_text_snippet": text_body[:2000] if text_body else None,
                "body_html_snippet": html_body[:2000] if html_body else None,
            },
        }

        result = ParsedBookingResult(**result_data)
        result.overall_confidence = self._compute_overall_confidence(result)
        result.needs_manual_review, result.review_reason = self._determine_review_status(result)
        return result

    # ------------------------------------------------------------------
    # HTML extraction
    # ------------------------------------------------------------------
    def _extract_from_html(self, html: str) -> tuple[dict[str, Any], dict[str, float]]:
        soup = BeautifulSoup(html, "lxml")
        data: dict[str, Any] = {}
        confidence: dict[str, float] = {}

        # Try to find key-value pairs in tables
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                cells = row.find_all(["td", "th"])
                if len(cells) >= 2:
                    label = self._normalize_text(cells[0].get_text())
                    value = self._normalize_text(cells[1].get_text())
                    self._apply_kv(label, value, data, confidence)

        # Also look for div/span/p patterns where label and value are adjacent
        for elem in soup.find_all(["div", "p", "span", "li"]):
            text = self._normalize_text(elem.get_text())
            self._apply_text_patterns(text, data, confidence, source="html")

        return data, confidence

    # ------------------------------------------------------------------
    # Text extraction
    # ------------------------------------------------------------------
    def _extract_from_text(self, text: str) -> tuple[dict[str, Any], dict[str, float]]:
        data: dict[str, Any] = {}
        confidence: dict[str, float] = {}
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            self._apply_text_patterns(line, data, confidence, source="text")
        return data, confidence

    # ------------------------------------------------------------------
    # Shared extraction helpers
    # ------------------------------------------------------------------
    def _apply_kv(
        self,
        label: str,
        value: str,
        data: dict[str, Any],
        confidence: dict[str, float],
    ) -> None:
        """Map a label/value pair from HTML tables to data fields."""
        label_lower = label.lower()

        mapping: dict[str, tuple[str, callable[[str], Any], float]] = {
            "voucher number": ("voucher_number", lambda v: v.strip(), 1.0),
            "voucher no": ("voucher_number", lambda v: v.strip(), 1.0),
            "voucher #": ("voucher_number", lambda v: v.strip(), 1.0),
            "booking reference": ("ota_reference_id", lambda v: v.strip(), 1.0),
            "reference number": ("ota_reference_id", lambda v: v.strip(), 1.0),
            "booking id": ("ota_reference_id", lambda v: v.strip(), 1.0),
            "hotel name": ("hotel_name", lambda v: v.strip(), 1.0),
            "property name": ("hotel_name", lambda v: v.strip(), 1.0),
            "hotel code": ("hotel_code", lambda v: v.strip(), 1.0),
            "room type name": ("room_type_name", lambda v: v.strip(), 1.0),
            "room type": ("room_type_name", lambda v: v.strip(), 1.0),
            "room code": ("room_code", lambda v: v.strip(), 1.0),
            "guest name": ("guest_name", lambda v: v.strip(), 1.0),
            "primary guest": ("guest_name", lambda v: v.strip(), 1.0),
            "booked by": ("guest_name", lambda v: v.strip(), 1.0),
            "guest email": ("guest_email", lambda v: v.strip(), 1.0),
            "email": ("guest_email", lambda v: v.strip(), 0.8),
            "check-in date": ("check_in", self._parse_date, 1.0),
            "check in": ("check_in", self._parse_date, 1.0),
            "arrival date": ("check_in", self._parse_date, 1.0),
            "check-out date": ("check_out", self._parse_date, 1.0),
            "check out": ("check_out", self._parse_date, 1.0),
            "departure date": ("check_out", self._parse_date, 1.0),
            "number of rooms": ("number_of_rooms", self._parse_int, 1.0),
            "rooms": ("number_of_rooms", self._parse_int, 0.8),
            "guests": ("number_of_guests", self._parse_guests, 1.0),
            "occupancy": ("number_of_guests", self._parse_guests, 0.9),
            "total amount": ("gross_amount", self._parse_amount, 1.0),
            "gross amount": ("gross_amount", self._parse_amount, 1.0),
            "amount paid": ("gross_amount", self._parse_amount, 1.0),
            "commission": ("ota_commission", self._parse_amount, 1.0),
            "commission fee": ("ota_commission", self._parse_amount, 1.0),
            "net payable": ("net_payout", self._parse_amount, 1.0),
            "net payout": ("net_payout", self._parse_amount, 1.0),
            "you receive": ("net_payout", self._parse_amount, 1.0),
            "special requests": ("special_requests", lambda v: v.strip(), 1.0),
            "special request": ("special_requests", lambda v: v.strip(), 1.0),
            "booking date": ("booking_date", self._parse_date, 1.0),
            "booked on": ("booking_date", self._parse_date, 1.0),
        }

        for key_label, (field, parser, conf) in mapping.items():
            if key_label in label_lower:
                if data.get(field) is None:
                    parsed = parser(value)
                    if parsed is not None:
                        data[field] = parsed
                        confidence[field] = conf
                break

    def _apply_text_patterns(
        self,
        text: str,
        data: dict[str, Any],
        confidence: dict[str, float],
        source: str = "text",
    ) -> None:
        base_conf = 0.9 if source == "text" else 0.85
        for field, patterns in self._RE_PATTERNS.items():
            if data.get(field) is not None:
                continue
            for pat in patterns:
                match = pat.search(text)
                if match:
                    raw = match.group(1).strip()
                    parsed = self._parse_field(field, raw)
                    if parsed is not None:
                        data[field] = parsed
                        confidence[field] = base_conf
                    break

    def _parse_field(self, field: str, raw: str) -> Any:
        if field in ("check_in", "check_out", "booking_date"):
            return self._parse_date(raw)
        if field in ("gross_amount", "ota_commission", "net_payout"):
            return self._parse_amount(raw)
        if field == "number_of_rooms":
            return self._parse_int(raw)
        if field == "number_of_guests":
            return self._parse_guests(raw)
        return raw if raw else None

    # ------------------------------------------------------------------
    # Normalization / parsing utilities
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_text(text: str) -> str:
        return " ".join(text.split())

    @staticmethod
    def _parse_int(value: str) -> Optional[int]:
        try:
            cleaned = re.sub(r"[^0-9]", "", value)
            return int(cleaned) if cleaned else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_amount(value: str) -> Optional[float]:
        try:
            cleaned = re.sub(r"[₹,Rs\sINR]", "", value, flags=re.IGNORECASE)
            cleaned = cleaned.replace(",", "")
            return float(cleaned) if cleaned else None
        except (ValueError, TypeError):
            return None

    def _parse_date(self, value: str) -> Optional[date]:
        value = value.strip()
        # Remove ordinal suffixes (1st, 2nd, 3rd, 4th)
        value = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", value, flags=re.IGNORECASE)
        for fmt in self._DATE_FORMATS:
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        # Try a few regex-based extractions for mixed formats
        m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", value)
        if m:
            day, month_str, year = m.groups()
            for fmt in (f"%d %b %Y", f"%d %B %Y"):
                try:
                    return datetime.strptime(f"{day} {month_str} {year}", fmt).date()
                except ValueError:
                    continue
        return None

    @staticmethod
    def _parse_guests(value: str) -> Optional[int]:
        # Patterns like "3 Adults, 1 Child" or "2 Adults"
        total = 0
        found = False
        for m in re.finditer(r"(\d+)\s*(?:Adults?|Child(?:ren)?|Kids?|Guests?)", value, re.IGNORECASE):
            total += int(m.group(1))
            found = True
        if found:
            return total
        # Fallback: just grab any standalone number near the word guest
        m = re.search(r"(\d+)\s*(?:guests?|occupants?|people?|persons?|travellers?)", value, re.IGNORECASE)
        if m:
            return int(m.group(1))
        return None

    # ------------------------------------------------------------------
    # Listing ID builder
    # ------------------------------------------------------------------
    @staticmethod
    def _build_listing_id(data: dict[str, Any]) -> Optional[str]:
        hotel_code = data.get("hotel_code")
        room_code = data.get("room_code")
        if hotel_code and room_code:
            return f"{hotel_code}:{room_code}"
        hotel_name = data.get("hotel_name")
        room_type_name = data.get("room_type_name")
        if hotel_name and room_type_name:
            return f"{hotel_name}|{room_type_name}"
        return hotel_code or room_code or hotel_name or room_type_name or None

    # ------------------------------------------------------------------
    # Confidence & review logic
    # ------------------------------------------------------------------
    _SCORED_FIELDS = [
        "ota_reference_id",
        "guest_name",
        "guest_email",
        "check_in",
        "check_out",
        "listing_id",
        "number_of_guests",
        "gross_amount",
        "ota_commission",
        "net_payout",
        "special_requests",
        "booking_date",
        "voucher_number",
        "hotel_name",
        "room_type_name",
        "number_of_rooms",
    ]

    def _compute_overall_confidence(self, result: ParsedBookingResult) -> float:
        if not result.confidence_scores:
            return 0.0
        scores = [result.confidence_scores.get(f, 0.0) for f in self._SCORED_FIELDS]
        return round(sum(scores) / len(scores), 2)

    def _determine_review_status(self, result: ParsedBookingResult) -> tuple[bool, Optional[str]]:
        reasons: list[str] = []
        if result.overall_confidence < 0.8:
            reasons.append(f"Overall confidence {result.overall_confidence} < 0.8")
        if not result.ota_reference_id:
            reasons.append("Missing booking reference")
        if not result.check_in:
            reasons.append("Missing check-in date")
        if not result.check_out:
            reasons.append("Missing check-out date")
        if not result.gross_amount:
            reasons.append("Missing gross amount")
        if reasons:
            return True, "; ".join(reasons)
        return False, None
