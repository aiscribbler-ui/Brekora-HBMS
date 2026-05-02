import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    user_id: uuid.UUID,
    org_id: uuid.UUID,
    role: str | None = None,
    email: str | None = None,
    name: str | None = None,
) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "org_id": str(org_id),
        "role": role,
        "email": email,
        "name": name,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(user_id: uuid.UUID, org_id: uuid.UUID, jti: uuid.UUID) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "org_id": str(org_id),
        "type": "refresh",
        "jti": str(jti),
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def decode_access_token(token: str) -> dict | None:
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None
    return payload


def decode_refresh_token(token: str) -> dict | None:
    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        return None
    return payload


def create_temp_token(user_id: uuid.UUID, org_id: uuid.UUID) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=5)
    payload = {
        "sub": str(user_id),
        "org_id": str(org_id),
        "type": "2fa_temp",
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_temp_token(token: str) -> dict | None:
    payload = decode_token(token)
    if not payload or payload.get("type") != "2fa_temp":
        return None
    return payload
