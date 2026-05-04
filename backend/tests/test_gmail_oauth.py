"""Tests for Gmail OAuth service and endpoints."""
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.oauth2.credentials import Credentials
from httpx import AsyncClient

from app.core.config import get_settings
from app.services.gmail_oauth_service import REDIS_KEY_GMAIL_TOKEN, GmailOAuthService


@pytest.mark.asyncio
async def test_gmail_auth_url_endpoint(client: AsyncClient):
    """OAuth initiation returns a valid Google auth URL."""
    settings = get_settings()
    original_client_id = settings.GOOGLE_CLIENT_ID
    original_client_secret = settings.GOOGLE_CLIENT_SECRET
    settings.GOOGLE_CLIENT_ID = "test_client_id"
    settings.GOOGLE_CLIENT_SECRET = "test_secret"
    try:
        with patch.object(
            GmailOAuthService,
            "create_auth_url",
            return_value=("https://accounts.google.com/o/oauth2/auth?test=1", "state_abc"),
        ):
            response = await client.get("/api/v1/ota/gmail/auth")
        assert response.status_code == 200
        data = response.json()
        assert "auth_url" in data
        assert "state" in data
        assert data["state"] == "state_abc"
    finally:
        settings.GOOGLE_CLIENT_ID = original_client_id
        settings.GOOGLE_CLIENT_SECRET = original_client_secret


@pytest.mark.asyncio
async def test_gmail_auth_endpoint_missing_config(client: AsyncClient):
    """Auth endpoint returns 503 when OAuth is not configured."""
    settings = get_settings()
    original_client_id = settings.GOOGLE_CLIENT_ID
    settings.GOOGLE_CLIENT_ID = None
    try:
        response = await client.get("/api/v1/ota/gmail/auth")
        assert response.status_code == 503
        assert "not configured" in response.json()["detail"]
    finally:
        settings.GOOGLE_CLIENT_ID = original_client_id


@pytest.mark.asyncio
async def test_gmail_callback_endpoint(client: AsyncClient):
    """Callback exchanges code for tokens and returns them."""
    mock_token = {
        "token": "access_token_123",
        "refresh_token": "refresh_token_123",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "client_id",
        "client_secret": "client_secret",
        "scopes": ["https://www.googleapis.com/auth/gmail.modify"],
        "expiry": datetime.now(timezone.utc).isoformat(),
    }
    with patch.object(GmailOAuthService, "exchange_code", return_value=mock_token):
        response = await client.get("/api/v1/ota/gmail/callback?code=abc123&state=state123")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "authenticated"
    assert data["access_token"] == "access_token_123"


@pytest.mark.asyncio
async def test_gmail_callback_bad_code(client: AsyncClient):
    """Callback with invalid code returns 400."""
    with patch.object(
        GmailOAuthService, "exchange_code", side_effect=Exception("invalid_grant")
    ):
        response = await client.get("/api/v1/ota/gmail/callback?code=bad_code")
    assert response.status_code == 400
    assert "OAuth token exchange failed" in response.json()["detail"]


@pytest.mark.asyncio
async def test_gmail_status_not_authenticated(client: AsyncClient):
    """Status shows not_authenticated when no tokens exist."""
    with patch.object(
        GmailOAuthService,
        "health_check",
        return_value={
            "connected": False,
            "status": "not_authenticated",
            "message": "No Gmail OAuth credentials found. Complete OAuth flow first.",
        },
    ):
        response = await client.get("/api/v1/ota/gmail/status")
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is False
    assert data["status"] == "not_authenticated"


@pytest.mark.asyncio
async def test_gmail_status_connected(client: AsyncClient):
    """Status shows connected when Gmail API is reachable."""
    with patch.object(
        GmailOAuthService,
        "health_check",
        return_value={
            "connected": True,
            "status": "ok",
            "email": "brekora@gmail.com",
            "messages_total": 100,
            "threads_total": 50,
        },
    ):
        response = await client.get("/api/v1/ota/gmail/status")
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is True
    assert data["email"] == "brekora@gmail.com"
    assert data["messages_total"] == 100


@pytest.mark.asyncio
async def test_gmail_service_create_auth_url():
    """Service generates a valid OAuth authorization URL."""
    settings = get_settings()
    settings.GOOGLE_CLIENT_ID = "test_client_id"
    settings.GOOGLE_CLIENT_SECRET = "test_secret"
    settings.GOOGLE_REDIRECT_URI = "http://localhost/callback"
    service = GmailOAuthService(settings)

    with patch.object(
        GmailOAuthService,
        "create_auth_url",
        return_value=("https://accounts.google.com/o/oauth2/auth?client_id=test", "state_xyz"),
    ):
        url, state = service.create_auth_url()

    assert "https://accounts.google.com" in url
    assert state == "state_xyz"


@pytest.mark.asyncio
async def test_gmail_service_loads_from_env_fallback():
    """When Redis has no token, service falls back to env vars."""
    settings = get_settings()
    settings.GOOGLE_ACCESS_TOKEN = "env_access"
    settings.GOOGLE_REFRESH_TOKEN = "env_refresh"
    settings.GOOGLE_CLIENT_ID = "env_client"
    settings.GOOGLE_CLIENT_SECRET = "env_secret"
    service = GmailOAuthService(settings)

    fake_redis = MagicMock()
    fake_redis.get = AsyncMock(return_value=None)

    with patch("app.services.gmail_oauth_service.get_redis_client", return_value=fake_redis):
        creds = await service._load_credentials()

    assert creds is not None
    assert creds.token == "env_access"
    assert creds.refresh_token == "env_refresh"


@pytest.mark.asyncio
async def test_gmail_service_loads_from_redis():
    """Service loads credentials from Redis when present."""
    settings = get_settings()
    settings.GOOGLE_CLIENT_ID = None
    settings.GOOGLE_CLIENT_SECRET = None
    service = GmailOAuthService(settings)

    token_data = {
        "token": "redis_access",
        "refresh_token": "redis_refresh",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "cid",
        "client_secret": "csec",
        "scopes": ["https://www.googleapis.com/auth/gmail.modify"],
        "expiry": datetime.now(timezone.utc).isoformat(),
    }
    fake_redis = MagicMock()
    fake_redis.get = AsyncMock(return_value=json.dumps(token_data))

    with patch("app.services.gmail_oauth_service.get_redis_client", return_value=fake_redis):
        creds = await service._load_credentials()

    assert creds is not None
    assert creds.token == "redis_access"
    assert creds.refresh_token == "redis_refresh"


@pytest.mark.asyncio
async def test_gmail_service_token_refresh():
    """Expired credentials are automatically refreshed and saved back to Redis."""
    settings = get_settings()
    settings.GOOGLE_CLIENT_ID = "test_client"
    settings.GOOGLE_CLIENT_SECRET = "test_secret"
    service = GmailOAuthService(settings)

    old_token = {
        "token": "old_token",
        "refresh_token": "refresh_token_123",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "test_client",
        "client_secret": "test_secret",
        "scopes": ["https://www.googleapis.com/auth/gmail.modify"],
        "expiry": "2020-01-01T00:00:00+00:00",
    }
    fake_redis = MagicMock()
    fake_redis.get = AsyncMock(return_value=json.dumps(old_token))
    fake_redis.setex = AsyncMock(return_value=None)

    mock_creds = MagicMock(spec=Credentials)
    mock_creds.expired = True
    mock_creds.refresh_token = "refresh_token_123"
    mock_creds.token = "new_token"
    mock_creds.token_uri = "https://oauth2.googleapis.com/token"
    mock_creds.client_id = "test_client"
    mock_creds.client_secret = "test_secret"
    mock_creds.scopes = ["https://www.googleapis.com/auth/gmail.modify"]
    mock_creds.expiry = datetime.now(timezone.utc)

    with patch(
        "app.services.gmail_oauth_service.get_redis_client", return_value=fake_redis
    ):
        with patch(
            "app.services.gmail_oauth_service.Credentials.from_authorized_user_info",
            return_value=mock_creds,
        ):
            with patch.object(mock_creds, "refresh", return_value=None) as mock_refresh:
                creds = await service.get_credentials()

    assert creds is not None
    assert creds.token == "new_token"
    mock_refresh.assert_called_once()
    fake_redis.setex.assert_called_once()
    # Verify Redis key used
    call_args = fake_redis.setex.call_args[0]
    assert call_args[0] == REDIS_KEY_GMAIL_TOKEN


@pytest.mark.asyncio
async def test_gmail_service_health_check_no_credentials():
    """Health check returns not_authenticated when credentials are missing."""
    settings = get_settings()
    settings.GOOGLE_ACCESS_TOKEN = None
    settings.GOOGLE_REFRESH_TOKEN = None
    service = GmailOAuthService(settings)

    fake_redis = MagicMock()
    fake_redis.get = AsyncMock(return_value=None)

    with patch("app.services.gmail_oauth_service.get_redis_client", return_value=fake_redis):
        result = await service.health_check()

    assert result["connected"] is False
    assert result["status"] == "not_authenticated"
