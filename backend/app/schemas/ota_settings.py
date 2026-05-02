import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OTASettingsBase(BaseModel):
    ota_source: str
    auto_confirm: bool = False
    min_confidence: float = 0.95
    is_active: bool = True


class OTASettingsCreate(OTASettingsBase):
    org_id: uuid.UUID | None = None


class OTASettingsUpdate(BaseModel):
    auto_confirm: bool | None = None
    min_confidence: float | None = None
    is_active: bool | None = None


class OTASettingsRead(OTASettingsBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
