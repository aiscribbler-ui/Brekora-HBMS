from __future__ import annotations

import datetime
import uuid

from pydantic import BaseModel, ConfigDict


class InventoryBufferBase(BaseModel):
    property_id: uuid.UUID
    room_type_id: uuid.UUID | None = None
    date: datetime.date
    buffer_count: int = 0
    reason: str | None = None


class InventoryBufferCreate(InventoryBufferBase):
    org_id: uuid.UUID | None = None


class InventoryBufferUpdate(BaseModel):
    property_id: uuid.UUID | None = None
    room_type_id: uuid.UUID | None = None
    date: datetime.date | None = None
    buffer_count: int | None = None
    reason: str | None = None


class InventoryBufferRead(InventoryBufferBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime
