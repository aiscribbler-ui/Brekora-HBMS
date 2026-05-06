import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.user import UserRead


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


class SetupRequest(BaseModel):
    org_name: str
    admin_email: str
    admin_password: str
    admin_name: str | None = None
