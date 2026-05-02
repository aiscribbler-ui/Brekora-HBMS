import uuid
from datetime import datetime

from pydantic import BaseModel


class GmailStatusResponse(BaseModel):
    connected: bool
    status: str
    message: str | None = None
    email: str | None = None
    messages_total: int | None = None
    threads_total: int | None = None


class GmailAuthUrlResponse(BaseModel):
    auth_url: str
    state: str


class GmailCallbackResponse(BaseModel):
    status: str
    access_token: str
    expires_at: str | None = None
