import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserBase(BaseModel):
    email: EmailStr
    phone: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    is_active: bool = True
    is_2fa_enabled: bool = False


class UserCreate(UserBase):
    org_id: uuid.UUID | None = None
    password: str = Field(..., min_length=10)
    role_id: uuid.UUID | None = None

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c in '!@#$%^&*()_+-=[]{};\':\"|,.\u003c>/?' for c in v):
            raise ValueError("Password must contain at least one special character")
        return v


class UserUpdate(UserBase):
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=10)
    role_id: uuid.UUID | None = None
    is_active: bool | None = None

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c in '!@#$%^&*()_+-=[]{};\':\"|,.\u003c>/?' for c in v):
            raise ValueError("Password must contain at least one special character")
        return v


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
