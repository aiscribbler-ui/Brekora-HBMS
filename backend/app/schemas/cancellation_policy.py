from decimal import Decimal
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class CancellationPolicyBase(BaseModel):
    name: str
    free_cancellation_hours: int | None = None
    partial_refund_hours: int | None = None
    partial_refund_percentage: Decimal | None = None
    non_refundable_hours: int | None = None
    is_non_refundable: bool = False


class CancellationPolicyCreate(CancellationPolicyBase):
    org_id: uuid.UUID | None = None


class CancellationPolicyUpdate(CancellationPolicyBase):
    name: str | None = None
    free_cancellation_hours: int | None = None
    partial_refund_hours: int | None = None
    partial_refund_percentage: Decimal | None = None
    non_refundable_hours: int | None = None
    is_non_refundable: bool | None = None


class CancellationPolicyRead(CancellationPolicyBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
