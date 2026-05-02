from decimal import Decimal
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class RoomTypeBase(BaseModel):
    name: str
    description: str | None = None
    count: int = 0
    base_capacity: int = 1
    max_capacity: int = 1
    default_rate: Decimal = Decimal("0.00")
    min_stay: int | None = None
    max_stay: int | None = None
    photos: list[dict[str, Any]] | None = None
    is_active: bool = True


class RoomTypeCreate(RoomTypeBase):
    org_id: uuid.UUID | None = None


class RoomTypeUpdate(RoomTypeBase):
    name: str | None = None
    count: int | None = None
    base_capacity: int | None = None
    max_capacity: int | None = None
    default_rate: Decimal | None = None
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
