from decimal import Decimal
import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


# --- Rate Plan Schemas ---

class RatePlanBase(BaseModel):
    name: str
    code: str
    discount_type: str = "percentage"
    discount_value: Decimal = Decimal("0.00")
    min_nights: int | None = None
    max_nights: int | None = None
    is_active: bool = True


class RatePlanCreate(RatePlanBase):
    org_id: uuid.UUID | None = None


class RatePlanUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    discount_type: str | None = None
    discount_value: Decimal | None = None
    min_nights: int | None = None
    max_nights: int | None = None
    is_active: bool | None = None


class RatePlanRead(RatePlanBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# --- Seasonal Calendar Schemas ---

class SeasonalCalendarBase(BaseModel):
    name: str
    start_date: date
    end_date: date
    multiplier: Decimal = Decimal("1.00")
    is_active: bool = True


class SeasonalCalendarCreate(SeasonalCalendarBase):
    org_id: uuid.UUID | None = None


class SeasonalCalendarUpdate(BaseModel):
    name: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    multiplier: Decimal | None = None
    is_active: bool | None = None


class SeasonalCalendarRead(SeasonalCalendarBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# --- Promo Code Schemas ---

class PromoCodeBase(BaseModel):
    code: str
    discount_type: str = "percentage"
    discount_value: Decimal = Decimal("0.00")
    max_uses: int | None = None
    used_count: int = 0
    valid_from: date | None = None
    valid_to: date | None = None
    applicable_booking_types: list[str] | None = None
    is_active: bool = True


class PromoCodeCreate(PromoCodeBase):
    org_id: uuid.UUID | None = None


class PromoCodeUpdate(BaseModel):
    code: str | None = None
    discount_type: str | None = None
    discount_value: Decimal | None = None
    max_uses: int | None = None
    used_count: int | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    applicable_booking_types: list[str] | None = None
    is_active: bool | None = None


class PromoCodeRead(PromoCodeBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# --- Price Calculation Schemas ---

class PriceBreakdown(BaseModel):
    subtotal: Decimal
    discount_amount: Decimal
    taxable_amount: Decimal
    tax_amount: Decimal
    gst_rate: Decimal = Decimal("0.12")
    channel_markup_amount: Decimal = Decimal("0.00")
    total_amount: Decimal
    currency: str
    breakdown_per_night: list[dict[str, Any]]
