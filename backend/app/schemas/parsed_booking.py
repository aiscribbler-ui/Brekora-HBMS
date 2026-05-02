from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ParsedBookingResult(BaseModel):
    """Canonical parsed booking output from any OTA email parser."""

    model_config = ConfigDict(from_attributes=True)

    # Core fields (common across OTAs)
    ota_reference_id: Optional[str] = None
    guest_name: Optional[str] = None
    guest_email: Optional[str] = None
    check_in: Optional[date] = None
    check_out: Optional[date] = None
    listing_id: Optional[str] = None  # OTA-specific property+room identifier
    number_of_guests: Optional[int] = None
    gross_amount: Optional[float] = None
    ota_commission: Optional[float] = None
    net_payout: Optional[float] = None
    special_requests: Optional[str] = None
    booking_date: Optional[date] = None

    # MakeMyTrip-specific fields
    voucher_number: Optional[str] = None
    hotel_name: Optional[str] = None
    room_type_name: Optional[str] = None
    number_of_rooms: Optional[int] = None

    # Goibibo-specific fields
    booking_reference: Optional[str] = None
    hotel_id: Optional[str] = None
    room_details: Optional[str] = None

    # Confidence & review metadata
    confidence_scores: dict[str, float] = Field(default_factory=dict)
    overall_confidence: float = 0.0
    needs_manual_review: bool = False
    review_reason: Optional[str] = None

    # Raw payload for debugging / re-parsing
    raw_payload: Optional[dict[str, Any]] = None
