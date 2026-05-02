from decimal import Decimal
import uuid
from datetime import date, datetime, time
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class AddOnSelection(BaseModel):
    add_on_id: uuid.UUID
    date: date
    quantity: int = 1
    slot_time: time | None = None


class BookingInitRequest(BaseModel):
    property_id: uuid.UUID
    item_type: Literal["room", "package"]
    item_id: uuid.UUID
    check_in: date
    check_out: date
    guests: int = 1
    add_on_selections: list[AddOnSelection] | None = None
    rate_plan_code: str | None = None
    promo_code: str | None = None
    channel_source: str | None = None
    guest_id: uuid.UUID | None = None
    idempotency_key: str | None = None
    notes: str | None = None


class AmountBreakdown(BaseModel):
    subtotal: Decimal
    discount_amount: Decimal
    taxable_amount: Decimal
    tax_amount: Decimal
    channel_markup_amount: Decimal
    total_amount: Decimal
    currency: str
    breakdown_per_night: list[dict[str, Any]]


class BookingInitResponse(BaseModel):
    booking_id: uuid.UUID
    hold_id: str
    hold_expires_at: datetime
    amount_breakdown: AmountBreakdown


class BookingLineItemBase(BaseModel):
    item_type: str
    item_id: uuid.UUID
    quantity: int = 1
    unit_price: Decimal = Decimal("0.00")
    nights: int = 1
    total_price: Decimal = Decimal("0.00")


class BookingLineItemCreate(BookingLineItemBase):
    pass


class BookingLineItemUpdate(BookingLineItemBase):
    item_type: str | None = None
    item_id: uuid.UUID | None = None
    quantity: int | None = None
    unit_price: Decimal | None = None
    nights: int | None = None
    total_price: Decimal | None = None


class BookingLineItemRead(BookingLineItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    booking_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class BookingBase(BaseModel):
    booking_type: str
    source_type: str = "direct"
    source_reference: str | None = None
    property_id: uuid.UUID
    guest_id: uuid.UUID | None = None
    check_in: date
    check_out: date
    status: str = "pending_payment"
    line_items: list[dict[str, Any]] | None = None
    gross_amount: Decimal = Decimal("0.00")
    discount_amount: Decimal = Decimal("0.00")
    tax_amount: Decimal = Decimal("0.00")
    total_amount: Decimal = Decimal("0.00")
    currency: str = "INR"
    cancellation_policy_snapshot: dict[str, Any] | None = None
    partner_attribution_id: str | None = None
    payment_state: str | None = None
    idempotency_key: str | None = None
    notes: str | None = None


class BookingCreate(BookingBase):
    org_id: uuid.UUID | None = None
    line_items_data: list[BookingLineItemCreate] | None = None


class BookingUpdate(BaseModel):
    status: str | None = None
    check_in: date | None = None
    check_out: date | None = None
    line_items: list[dict[str, Any]] | None = None
    gross_amount: Decimal | None = None
    discount_amount: Decimal | None = None
    tax_amount: Decimal | None = None
    total_amount: Decimal | None = None
    currency: str | None = None
    cancellation_policy_snapshot: dict[str, Any] | None = None
    payment_state: str | None = None
    idempotency_key: str | None = None
    notes: str | None = None
    cancelled_at: datetime | None = None
    cancellation_reason: str | None = None
    guest_id: uuid.UUID | None = None


class BookingModificationRequest(BaseModel):
    check_in: date | None = None
    check_out: date | None = None
    room_type_id: uuid.UUID | None = None
    add_ons: list[AddOnSelection] | None = None
    guest_details: dict[str, Any] | None = None
    reason: str | None = None


class BookingRead(BookingBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    cancelled_at: datetime | None = None
    cancellation_reason: str | None = None
    line_item_records: list[BookingLineItemRead] = []


class BookingModificationResponse(BookingRead):
    payment_difference: Decimal = Decimal("0.00")
    new_total: Decimal = Decimal("0.00")
    razorpay_order: dict[str, Any] | None = None
    refund_amount: Decimal | None = None
