import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import decode_access_token, decode_refresh_token
from app.repositories.user import UserRepository

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def _create_user(db_session: AsyncSession, email: str, password: str, is_active: bool = True):
    from app.core.security import get_password_hash

    repo = UserRepository(db_session, DEFAULT_ORG_ID)
    return await repo.create(
        {
            "email": email,
            "password_hash": get_password_hash(password),
            "first_name": "Test",
            "last_name": "User",
            "is_active": is_active,
        }
    )


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, db_session: AsyncSession):
    await _create_user(db_session, "login_success@example.com", "mypassword")

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "login_success@example.com", "password": "mypassword"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data
    assert data["expires_in"] == 15 * 60

    # Verify access token payload
    access_payload = decode_access_token(data["access_token"])
    assert access_payload is not None
    assert access_payload["type"] == "access"
    assert access_payload["sub"] is not None
    assert access_payload["org_id"] == str(DEFAULT_ORG_ID)

    # Verify refresh token payload
    refresh_payload = decode_refresh_token(data["refresh_token"])
    assert refresh_payload is not None
    assert refresh_payload["type"] == "refresh"
    assert refresh_payload["jti"] is not None
    assert refresh_payload["sub"] == access_payload["sub"]


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, db_session: AsyncSession):
    await _create_user(db_session, "login_badpass@example.com", "mypassword")

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "login_badpass@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_login_inactive_user(client: AsyncClient, db_session: AsyncSession):
    await _create_user(db_session, "login_inactive@example.com", "mypassword", is_active=False)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "login_inactive@example.com", "password": "mypassword"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_login_rate_limit(client: AsyncClient, db_session: AsyncSession):
    email = "ratelimit@example.com"
    await _create_user(db_session, email, "mypassword")

    # 5 failed attempts should be allowed
    for i in range(5):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "wrongpassword"},
        )
        assert response.status_code == 401

    # 6th attempt should be rate limited
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "wrongpassword"},
    )
    assert response.status_code == 429
    assert "Too many login attempts" in response.json()["detail"]

    # After rate limit is hit, further requests (even correct password) are blocked
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "mypassword"},
    )
    assert response.status_code == 429

    # Successful login on a fresh user should work and reset counter for that user
    email2 = "ratelimit2@example.com"
    await _create_user(db_session, email2, "mypassword")

    # 4 failed attempts
    for i in range(4):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": email2, "password": "wrongpassword"},
        )
        assert response.status_code == 401

    # Successful login resets the counter
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email2, "password": "mypassword"},
    )
    assert response.status_code == 200

    # After successful login, failed attempts should start fresh
    for i in range(5):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": email2, "password": "wrongpassword"},
        )
        assert response.status_code == 401

    # 6th failed attempt after reset should be rate limited again
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email2, "password": "wrongpassword"},
    )
    assert response.status_code == 429


@pytest.mark.asyncio
async def test_refresh_token_rotation(client: AsyncClient, db_session: AsyncSession):
    user = await _create_user(db_session, "refresh_test@example.com", "mypassword")

    # Login
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "refresh_test@example.com", "password": "mypassword"},
    )
    assert response.status_code == 200
    first_refresh = response.json()["refresh_token"]

    # Refresh
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first_refresh},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    second_refresh = data["refresh_token"]
    assert second_refresh != first_refresh

    # Old refresh token should be invalid (rotation)
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first_refresh},
    )
    assert response.status_code == 401

    # New refresh token should work
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": second_refresh},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_refresh_token_invalid(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid.token.here"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_access_token_rejected(client: AsyncClient, db_session: AsyncSession):
    user = await _create_user(db_session, "refresh_access@example.com", "mypassword")

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "refresh_access@example.com", "password": "mypassword"},
    )
    access_token = response.json()["access_token"]

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_invalidates_refresh_token(client: AsyncClient, db_session: AsyncSession):
    await _create_user(db_session, "logout_test@example.com", "mypassword")

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "logout_test@example.com", "password": "mypassword"},
    )
    refresh_token = response.json()["refresh_token"]

    # Logout
    response = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 204

    # Refresh should fail after logout
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_with_invalid_token(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": "totally.invalid.token"},
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_access_token_expiry(client: AsyncClient, db_session: AsyncSession):
    from unittest.mock import patch

    user = await _create_user(db_session, "expiry_test@example.com", "mypassword")

    with patch("app.core.security.get_settings") as mock_settings:
        settings = get_settings()
        mock_settings.return_value = settings

        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "expiry_test@example.com", "password": "mypassword"},
        )
        assert response.status_code == 200
        access_token = response.json()["access_token"]

        payload = decode_access_token(access_token)
        assert payload is not None
        iat = payload["iat"]
        exp = payload["exp"]
        assert exp - iat == 15 * 60  # 15 minutes in seconds
