import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RoleBase(BaseModel):
    name: str
    description: str | None = None


class RoleCreate(RoleBase):
    org_id: uuid.UUID | None = None


class RoleUpdate(RoleBase):
    name: str | None = None
    description: str | None = None


class RoleRead(RoleBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
