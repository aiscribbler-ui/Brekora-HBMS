import uuid
from datetime import datetime, time
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class PropertyBase(BaseModel):
    name: str
    address: str | None = None
    gstin: str | None = None
    pan: str | None = None
    owner_contact: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    photos: list[dict[str, Any]] | None = None
    amenities: list[str] | None = None
    default_check_in_time: time | None = None
    default_check_out_time: time | None = None
    cancellation_policy_id: uuid.UUID | None = None
    is_active: bool = True


class PropertyCreate(PropertyBase):
    org_id: uuid.UUID | None = None


class PropertyUpdate(PropertyBase):
    name: str | None = None
    is_active: bool | None = None
    is_archived: bool | None = None


class PropertyRead(PropertyBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    is_archived: bool
    created_at: datetime
    updated_at: datetime
