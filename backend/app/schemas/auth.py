import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.user import UserRead


class MeResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    email: str
    role: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    name: str | None = None
    is_2fa_enabled: bool = False
    is_active: bool = True
    last_login: datetime | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    session_id: str | None = None


class LoginResponse(BaseModel):
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int | None = None
    temp_token: str | None = None
    requires_2fa: bool = False
    session_id: str | None = None


class TwoFASetupResponse(BaseModel):
    secret: str
    provisioning_uri: str


class TwoFAVerifyRequest(BaseModel):
    secret: str
    token: str


class TwoFADisableRequest(BaseModel):
    token: str


class TwoFALoginVerifyRequest(BaseModel):
    temp_token: str
    token: str


class GoogleAuthRequest(BaseModel):
    id_token: str


class GoogleAuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    session_id: str
    user: UserRead


class SetupStatusResponse(BaseModel):
    setup_required: bool


class UserPropertyResponse(BaseModel):
    property_id: uuid.UUID
    name: str
    role_at_property: str


class SetupRequest(BaseModel):
    org_name: str
    admin_email: str
    admin_password: str
    admin_name: str | None = None
