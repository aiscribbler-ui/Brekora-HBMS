import uuid

import pytest
from httpx import AsyncClient
from pyotp import TOTP
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token, decode_refresh_token, decode_temp_token
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


async def _login_and_get_token(client: AsyncClient, email: str, password: str) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_setup_2fa_returns_provisioning_uri(client: AsyncClient, db_session: AsyncSession):
    user = await _create_user(db_session, "2fa_setup@example.com", "mypassword")
    access_token = await _login_and_get_token(client, user.email, "mypassword")

    response = await client.post(
        "/api/v1/auth/2fa/setup",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "secret" in data
    assert "provisioning_uri" in data
    assert data["provisioning_uri"].startswith("otpauth://totp/")


@pytest.mark.asyncio
async def test_verify_2fa_enables_2fa(client: AsyncClient, db_session: AsyncSession):
    user = await _create_user(db_session, "2fa_verify@example.com", "mypassword")
    access_token = await _login_and_get_token(client, user.email, "mypassword")

    # Setup
    setup_resp = await client.post(
        "/api/v1/auth/2fa/setup",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    secret = setup_resp.json()["secret"]
    token = TOTP(secret).now()

    # Verify
    response = await client.post(
        "/api/v1/auth/2fa/verify",
        json={"secret": secret, "token": token},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 204

    # Confirm user has 2FA enabled
    repo = UserRepository(db_session, DEFAULT_ORG_ID)
    updated_user = await repo.get(user.id)
    assert updated_user is not None
    assert updated_user.is_2fa_enabled is True
    assert updated_user.totp_secret == secret


@pytest.mark.asyncio
async def test_login_with_2fa_enabled_returns_temp_token(client: AsyncClient, db_session: AsyncSession):
    user = await _create_user(db_session, "2fa_login@example.com", "mypassword")
    access_token = await _login_and_get_token(client, user.email, "mypassword")

    setup_resp = await client.post(
        "/api/v1/auth/2fa/setup",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    secret = setup_resp.json()["secret"]
    token = TOTP(secret).now()

    await client.post(
        "/api/v1/auth/2fa/verify",
        json={"secret": secret, "token": token},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    # Login should return temp token
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "2fa_login@example.com", "password": "mypassword"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["requires_2fa"] is True
    assert data["temp_token"] is not None
    assert data["access_token"] is None
    assert data["refresh_token"] is None

    # Verify temp token payload
    temp_payload = decode_temp_token(data["temp_token"])
    assert temp_payload is not None
    assert temp_payload["type"] == "2fa_temp"
    assert temp_payload["sub"] == str(user.id)
    assert temp_payload["org_id"] == str(DEFAULT_ORG_ID)


@pytest.mark.asyncio
async def test_login_verify_with_valid_totp_returns_full_tokens(client: AsyncClient, db_session: AsyncSession):
    user = await _create_user(db_session, "2fa_login_verify@example.com", "mypassword")
    access_token = await _login_and_get_token(client, user.email, "mypassword")

    setup_resp = await client.post(
        "/api/v1/auth/2fa/setup",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    secret = setup_resp.json()["secret"]
    token = TOTP(secret).now()

    await client.post(
        "/api/v1/auth/2fa/verify",
        json={"secret": secret, "token": token},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    # Get temp token
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "2fa_login_verify@example.com", "password": "mypassword"},
    )
    temp_token = login_resp.json()["temp_token"]

    # Generate fresh TOTP
    fresh_token = TOTP(secret).now()

    response = await client.post(
        "/api/v1/auth/2fa/login-verify",
        json={"temp_token": temp_token, "token": fresh_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data

    # Verify token payloads
    access_payload = decode_access_token(data["access_token"])
    assert access_payload is not None
    assert access_payload["sub"] == str(user.id)

    refresh_payload = decode_refresh_token(data["refresh_token"])
    assert refresh_payload is not None
    assert refresh_payload["sub"] == str(user.id)


@pytest.mark.asyncio
async def test_login_verify_with_invalid_totp_returns_401(client: AsyncClient, db_session: AsyncSession):
    user = await _create_user(db_session, "2fa_invalid@example.com", "mypassword")
    access_token = await _login_and_get_token(client, user.email, "mypassword")

    setup_resp = await client.post(
        "/api/v1/auth/2fa/setup",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    secret = setup_resp.json()["secret"]
    token = TOTP(secret).now()

    await client.post(
        "/api/v1/auth/2fa/verify",
        json={"secret": secret, "token": token},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    # Get temp token
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "2fa_invalid@example.com", "password": "mypassword"},
    )
    temp_token = login_resp.json()["temp_token"]

    response = await client.post(
        "/api/v1/auth/2fa/login-verify",
        json={"temp_token": temp_token, "token": "000000"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid TOTP token"


@pytest.mark.asyncio
async def test_disable_2fa(client: AsyncClient, db_session: AsyncSession):
    user = await _create_user(db_session, "2fa_disable@example.com", "mypassword")
    access_token = await _login_and_get_token(client, user.email, "mypassword")

    setup_resp = await client.post(
        "/api/v1/auth/2fa/setup",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    secret = setup_resp.json()["secret"]
    token = TOTP(secret).now()

    await client.post(
        "/api/v1/auth/2fa/verify",
        json={"secret": secret, "token": token},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    # Disable with fresh TOTP
    disable_token = TOTP(secret).now()
    response = await client.post(
        "/api/v1/auth/2fa/disable",
        json={"token": disable_token},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 204

    repo = UserRepository(db_session, DEFAULT_ORG_ID)
    updated_user = await repo.get(user.id)
    assert updated_user is not None
    assert updated_user.is_2fa_enabled is False
    assert updated_user.totp_secret is None
