from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

import uuid


@dataclass
class CanonicalBooking:
    """Normalized booking representation across all ingest channels."""

    source_type: str
    source_reference: str | None = None
    property_id: uuid.UUID | None = None
    room_type_id: uuid.UUID | None = None
    guest_id: uuid.UUID | None = None
    guest_name: str | None = None
    guest_email: str | None = None
    check_in: date | None = None
    check_out: date | None = None
    number_of_guests: int | None = None
    gross_amount: Decimal = Decimal("0.00")
    discount_amount: Decimal = Decimal("0.00")
    tax_amount: Decimal = Decimal("0.00")
    total_amount: Decimal = Decimal("0.00")
    currency: str = "INR"
    line_items: list[dict[str, Any]] = field(default_factory=list)
    ota_commission: Decimal | None = None
    net_payout: Decimal | None = None
    special_requests: str | None = None
    booking_date: date | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_booking_create(self) -> dict[str, Any]:
        """Return a dict compatible with the BookingCreate schema."""
        payload = {
            "booking_type": "room",
            "source_type": self.source_type,
            "source_reference": self.source_reference,
            "property_id": self.property_id,
            "guest_id": self.guest_id,
            "check_in": self.check_in,
            "check_out": self.check_out,
            "status": "pending_payment",
            "line_items": self.line_items,
            "gross_amount": self.gross_amount,
            "discount_amount": self.discount_amount,
            "tax_amount": self.tax_amount,
            "total_amount": self.total_amount,
            "currency": self.currency,
            "notes": self.special_requests,
        }
        # Remove None values to let Pydantic defaults apply where appropriate
        return {k: v for k, v in payload.items() if v is not None}

    def to_line_items(self) -> list[dict[str, Any]]:
        """Build line-item dicts from the canonical room_type_id if present."""
        if not self.room_type_id:
            return []
        nights = 0
        if self.check_in and self.check_out:
            nights = (self.check_out - self.check_in).days
            if nights <= 0:
                nights = 1
        unit_price = Decimal("0.00")
        if self.total_amount and nights > 0:
            unit_price = Decimal(self.total_amount) / nights
        return [
            {
                "item_type": "room",
                "item_id": self.room_type_id,
                "quantity": 1,
                "unit_price": unit_price,
                "nights": nights,
                "total_price": self.total_amount,
            }
        ]
