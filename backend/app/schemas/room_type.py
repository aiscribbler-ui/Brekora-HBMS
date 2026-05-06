from decimal import Decimal
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RoomTypeBase(BaseModel):
    name: str
    description: str | None = None
    count: int = Field(default=0, ge=0)
    base_capacity: int = Field(default=1, ge=1)
    max_capacity: int = Field(default=1, ge=1)
    default_rate: Decimal = Field(default=Decimal("0.00"), ge=0)
    min_stay: int | None = Field(default=None, ge=1)
    max_stay: int | None = Field(default=None, ge=1)
    photos: list[dict[str, Any]] | None = None
    is_active: bool = True


class RoomTypeCreate(RoomTypeBase):
    org_id: uuid.UUID | None = None


class RoomTypeUpdate(RoomTypeBase):
    name: str | None = None
    count: int | None = Field(default=None, ge=0)
    base_capacity: int | None = Field(default=None, ge=1)
    max_capacity: int | None = Field(default=None, ge=1)
    default_rate: Decimal | None = Field(default=None, ge=0)
    min_stay: int | None = Field(default=None, ge=1)
    max_stay: int | None = Field(default=None, ge=1)
    is_active: bool | None = None
    is_archived: bool | None = None


class RoomTypeRead(RoomTypeBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    property_id: uuid.UUID
    is_archived: bool
    created_at: datetime
    updated_at: datetime
