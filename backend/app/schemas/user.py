import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    phone: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    is_active: bool = True
    is_2fa_enabled: bool = False


class UserCreate(UserBase):
    org_id: uuid.UUID | None = None
    password: str
    role_id: uuid.UUID | None = None


class UserUpdate(UserBase):
    email: EmailStr | None = None
    password: str | None = None
    role_id: uuid.UUID | None = None
    is_active: bool | None = None


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    role_id: uuid.UUID | None = None
    last_login: datetime | None = None
    google_id: str | None = None
    created_at: datetime
    updated_at: datetime


class UserLogin(BaseModel):
    email: EmailStr
    password: str
