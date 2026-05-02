from __future__ import annotations

import datetime
import uuid

from pydantic import BaseModel, ConfigDict


class FeatureFlagBase(BaseModel):
    key: str
    name: str
    description: str | None = None
    enabled: bool = False
    value: str | None = None
    scope: str = "org"


class FeatureFlagCreate(FeatureFlagBase):
    org_id: uuid.UUID | None = None


class FeatureFlagUpdate(BaseModel):
    key: str | None = None
    name: str | None = None
    description: str | None = None
    enabled: bool | None = None
    value: str | None = None
    scope: str | None = None


class FeatureFlagRead(FeatureFlagBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime
