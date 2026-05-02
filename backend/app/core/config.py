import os
import uuid
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_BREKORA_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENVIRONMENT: Literal["development", "testing", "production"] = "development"
    DEBUG: bool = False

    DATABASE_URL: str = Field(...)
    SECRET_KEY: str = Field(...)
    REDIS_URL: str = Field(...)

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    DEFAULT_ORG_ID: uuid.UUID = DEFAULT_BREKORA_ORG_ID
    UPLOAD_DIR: str = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")

    TOTP_ENCRYPTION_KEY: str = Field(...)

    SENTRY_DSN: str | None = None
    LOG_LEVEL: str = "INFO"

    # Gmail OAuth (MVP: single Brekora mailbox)
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/ota/gmail/callback"
    GOOGLE_ACCESS_TOKEN: str | None = None
    GOOGLE_REFRESH_TOKEN: str | None = None

    # Razorpay (test mode in MVP)
    RAZORPAY_KEY_ID: str | None = None
    RAZORPAY_KEY_SECRET: str | None = None
    RAZORPAY_WEBHOOK_SECRET: str | None = None

    @property
    def sync_database_url(self) -> str:
        return (
            self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg://")
            .replace("postgresql+psycopg_async://", "postgresql+psycopg://")
            .replace("postgresql://", "postgresql+psycopg://")
        )

    @property
    def async_database_url(self) -> str:
        return (
            self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
            .replace("postgresql+psycopg://", "postgresql+asyncpg://")
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
