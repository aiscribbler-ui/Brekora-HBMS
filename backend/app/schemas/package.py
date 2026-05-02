from decimal import Decimal
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class PackageCompositionBase(BaseModel):
    room_type_id: uuid.UUID
    quantity: int = 1
    nights: int = 1


class PackageCompositionCreate(PackageCompositionBase):
    org_id: uuid.UUID | None = None


class PackageCompositionUpdate(PackageCompositionBase):
    room_type_id: uuid.UUID | None = None
    quantity: int | None = None
    nights: int | None = None


class PackageCompositionRead(PackageCompositionBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    package_id: uuid.UUID
    org_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class PackageAddOnBase(BaseModel):
    add_on_id: uuid.UUID
    quantity: int = 1
    is_included: bool = False


class PackageAddOnCreate(PackageAddOnBase):
    org_id: uuid.UUID | None = None


class PackageAddOnUpdate(PackageAddOnBase):
    add_on_id: uuid.UUID | None = None
    quantity: int | None = None
    is_included: bool | None = None


class PackageAddOnRead(PackageAddOnBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    package_id: uuid.UUID
    org_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class PackageBase(BaseModel):
    name: str
    description: str | None = None
    status: str = "draft"
    base_price: Decimal = Decimal("0.00")
    dynamic_pricing_rules: dict[str, Any] | None = None
    date_constraints: dict[str, Any] | None = None
    max_occupancy: int | None = None
    cancellation_policy_id: uuid.UUID | None = None
    is_active: bool = True


class PackageCreate(PackageBase):
    property_id: uuid.UUID
    org_id: uuid.UUID | None = None


class PackageUpdate(PackageBase):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    base_price: Decimal | None = None
    dynamic_pricing_rules: dict[str, Any] | None = None
    date_constraints: dict[str, Any] | None = None
    max_occupancy: int | None = None
    cancellation_policy_id: uuid.UUID | None = None
    is_active: bool | None = None
    is_archived: bool | None = None


class PackageRead(PackageBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    property_id: uuid.UUID
    org_id: uuid.UUID
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    compositions: list[PackageCompositionRead] = []
    add_ons: list[PackageAddOnRead] = []
