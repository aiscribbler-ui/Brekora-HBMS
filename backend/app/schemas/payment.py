import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PaymentBase(BaseModel):
    amount: Decimal
    currency: str = "INR"
    provider: str = "razorpay"
    provider_order_id: str
    provider_payment_id: str | None = None
    status: str = "created"


class PaymentCreate(PaymentBase):
    org_id: uuid.UUID
    booking_id: uuid.UUID


class PaymentRead(PaymentBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    booking_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class OrderCreateRequest(BaseModel):
    booking_id: uuid.UUID


class OrderCreateResponse(BaseModel):
    order_id: str
    amount: int
    currency: str
    status: str
