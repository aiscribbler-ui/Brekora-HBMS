import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.repositories.user import UserRepository

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.mark.asyncio
async def test_google_login_creates_guest_user(
    client: AsyncClient, db_session: AsyncSession
):
    mock_payload = {
        "sub": "google_12345",
        "email": "google_new@example.com",
        "name": "Google User",
        "picture": "https://example.com/pic.png",
        "iss": "https://accounts.google.com",
    }

    with patch(
        "app.services.google_oauth_service.id_token.verify_oauth2_token",
        return_value=mock_payload,
    ):
        response = await client.post(
            "/api/v1/auth/google",
            json={"id_token": "fake_token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "session_id" in data
        assert data["user"]["email"] == "google_new@example.com"
        assert data["user"]["first_name"] == "Google User"

        repo = UserRepository(db_session, DEFAULT_ORG_ID)
        user = await repo.get_by_email("google_new@example.com")
        assert user is not None
        assert user.google_id == "google_12345"


@pytest.mark.asyncio
async def test_google_login_existing_user_links_account(
    client: AsyncClient, db_session: AsyncSession
):
    repo = UserRepository(db_session, DEFAULT_ORG_ID)
    user = await repo.create(
        {
            "email": "google_existing@example.com",
            "password_hash": get_password_hash("password"),
            "first_name": "Existing",
            "last_name": "User",
        }
    )
    assert user.google_id is None

    mock_payload = {
        "sub": "google_67890",
        "email": "google_existing@example.com",
        "name": "Existing User",
        "picture": "https://example.com/pic.png",
        "iss": "https://accounts.google.com",
    }

    with patch(
        "app.services.google_oauth_service.id_token.verify_oauth2_token",
        return_value=mock_payload,
    ):
        response = await client.post(
            "/api/v1/auth/google",
            json={"id_token": "fake_token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == "google_existing@example.com"

        updated_user = await repo.get_by_email("google_existing@example.com")
        assert updated_user.google_id == "google_67890"


@pytest.mark.asyncio
async def test_google_login_invalid_token(client: AsyncClient):
    with patch(
        "app.services.google_oauth_service.id_token.verify_oauth2_token",
        side_effect=ValueError("Invalid token"),
    ):
        response = await client.post(
            "/api/v1/auth/google",
            json={"id_token": "bad_token"},
        )
        assert response.status_code == 401
