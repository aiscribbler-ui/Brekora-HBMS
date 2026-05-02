import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RawEmailBase(BaseModel):
    gmail_message_id: str
    ota_source: str
    subject: str | None = None
    body_text: str | None = None
    body_html: str | None = None
    sender: str | None = None
    recipient: str | None = None
    received_at: datetime | None = None
    status: str = "pending"


class RawEmailCreate(RawEmailBase):
    org_id: uuid.UUID | None = None


class RawEmailUpdate(BaseModel):
    gmail_message_id: str | None = None
    ota_source: str | None = None
    subject: str | None = None
    body_text: str | None = None
    body_html: str | None = None
    sender: str | None = None
    recipient: str | None = None
    received_at: datetime | None = None
    status: str | None = None


class RawEmailRead(RawEmailBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
