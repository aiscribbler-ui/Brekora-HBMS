from decimal import Decimal
import uuid
from datetime import date as _date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict


class AddOnBase(BaseModel):
    name: str
    description: str | None = None
    type: Literal["slot", "day", "package_instance"] = "day"
    default_capacity: int = 0
    unit_price: Decimal = Decimal("0.00")
    is_active: bool = True


class AddOnCreate(AddOnBase):
    property_id: uuid.UUID
    org_id: uuid.UUID | None = None


class AddOnUpdate(AddOnBase):
    name: str | None = None
    description: str | None = None
    type: Literal["slot", "day", "package_instance"] | None = None
    default_capacity: int | None = None
    unit_price: Decimal | None = None
    is_active: bool | None = None
    is_archived: bool | None = None


class AddOnRead(AddOnBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    property_id: uuid.UUID
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class AddOnCapacityBase(BaseModel):
    date: _date
    slot_time: time | None = None
    available_capacity: int = 0
    total_capacity: int = 0


class AddOnCapacityCreate(AddOnCapacityBase):
    pass


class AddOnCapacityUpdate(BaseModel):
    date: _date | None = None
    slot_time: time | None = None
    available_capacity: int | None = None
    total_capacity: int | None = None


class AddOnCapacityRead(AddOnCapacityBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    add_on_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class GenerateCapacityRequest(BaseModel):
    start_date: _date
    end_date: _date
    slot_times: list[time] | None = None
