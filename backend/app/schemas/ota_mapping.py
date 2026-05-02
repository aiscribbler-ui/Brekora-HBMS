import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OTAMappingBase(BaseModel):
    ota_source: str
    listing_id: str
    room_type_id: uuid.UUID
    property_id: uuid.UUID
    is_active: bool = True


class OTAMappingCreate(OTAMappingBase):
    org_id: uuid.UUID | None = None


class OTAMappingUpdate(OTAMappingBase):
    ota_source: str | None = None
    listing_id: str | None = None
    room_type_id: uuid.UUID | None = None
    property_id: uuid.UUID | None = None
    is_active: bool | None = None
    is_archived: bool | None = None


class OTAMappingRead(OTAMappingBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    is_archived: bool
    created_at: datetime
    updated_at: datetime
