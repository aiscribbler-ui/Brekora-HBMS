"""Gmail API OAuth 2.0 service with automatic token refresh."""
import json
import logging
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import Settings
from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)

REDIS_KEY_GMAIL_TOKEN = "gmail:oauth_token"
REDIS_KEY_GMAIL_STATE = "gmail:oauth_state"
GMAIL_MODIFY_SCOPE = "https://www.googleapis.com/auth/gmail.modify"


class GmailOAuthService:
    """Handles Gmail OAuth flow, token storage in Redis, and automatic refresh."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _get_client_config(self) -> dict[str, Any]:
        return {
            "web": {
                "client_id": self.settings.GOOGLE_CLIENT_ID,
                "client_secret": self.settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.settings.GOOGLE_REDIRECT_URI],
            }
        }

    def create_auth_url(self, state: str | None = None) -> tuple[str, str]:
        """Generate the Google OAuth consent URL.

        Stores CSRF state in Redis with a 10-minute TTL.

        Returns
        -------
        tuple[str, str]
            (authorization_url, state)
        """
        flow = Flow.from_client_config(
            self._get_client_config(),
            scopes=[GMAIL_MODIFY_SCOPE],
            state=state,
        )
        flow.redirect_uri = self.settings.GOOGLE_REDIRECT_URI
        auth_url, generated_state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        return auth_url, generated_state

    async def store_state(self, state: str) -> None:
        """Store CSRF state in Redis with 10-minute TTL."""
        redis = await get_redis_client()
        await redis.setex(REDIS_KEY_GMAIL_STATE, 600, state)

    async def verify_state(self, state: str | None) -> bool:
        """Verify the OAuth callback state matches the stored value."""
        if not state:
            return False
        redis = await get_redis_client()
        stored = await redis.get(REDIS_KEY_GMAIL_STATE)
        return stored == state

    async def exchange_code(self, code: str, state: str | None = None) -> dict[str, Any]:
        """Exchange the OAuth authorization code for tokens and persist them."""
        flow = Flow.from_client_config(
            self._get_client_config(),
            scopes=[GMAIL_MODIFY_SCOPE],
            state=state,
        )
        flow.redirect_uri = self.settings.GOOGLE_REDIRECT_URI
        flow.fetch_token(code=code)
        credentials = flow.credentials

        token_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
            "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
        }

        redis = await get_redis_client()
        await redis.setex(REDIS_KEY_GMAIL_TOKEN, 30 * 24 * 60 * 60, json.dumps(token_data))
        logger.info("Gmail OAuth tokens stored in Redis")
        return token_data

    async def _load_credentials(self) -> Credentials | None:
        """Load credentials from Redis, falling back to env vars."""
        redis = await get_redis_client()
        token_json = await redis.get(REDIS_KEY_GMAIL_TOKEN)

        if token_json:
            token_data = json.loads(token_json)
            return Credentials.from_authorized_user_info(token_data)

        # Fallback to env vars for MVP
        if self.settings.GOOGLE_ACCESS_TOKEN and self.settings.GOOGLE_REFRESH_TOKEN:
            token_data = {
                "token": self.settings.GOOGLE_ACCESS_TOKEN,
                "refresh_token": self.settings.GOOGLE_REFRESH_TOKEN,
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": self.settings.GOOGLE_CLIENT_ID,
                "client_secret": self.settings.GOOGLE_CLIENT_SECRET,
                "scopes": [GMAIL_MODIFY_SCOPE],
            }
            return Credentials.from_authorized_user_info(token_data)

        return None

    async def _save_credentials(self, credentials: Credentials) -> None:
        """Persist refreshed credentials to Redis."""
        token_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
            "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
        }
        redis = await get_redis_client()
        await redis.setex(REDIS_KEY_GMAIL_TOKEN, 30 * 24 * 60 * 60, json.dumps(token_data))

    async def get_credentials(self) -> Credentials | None:
        """Return valid credentials, refreshing if necessary."""
        credentials = await self._load_credentials()
        if not credentials:
            return None

        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            await self._save_credentials(credentials)
            logger.info("Gmail access token refreshed automatically")

        return credentials

    async def disconnect(self) -> bool:
        """Remove stored Gmail OAuth tokens from Redis."""
        redis = await get_redis_client()
        result = await redis.delete(REDIS_KEY_GMAIL_TOKEN)
        await redis.delete(REDIS_KEY_GMAIL_STATE)
        logger.info("Gmail OAuth tokens removed from Redis")
        return result > 0

    async def health_check(self) -> dict[str, Any]:
        """Verify Gmail API connectivity and return status."""
        credentials = await self.get_credentials()
        if not credentials:
            return {
                "connected": False,
                "status": "not_authenticated",
                "message": "No Gmail OAuth credentials found. Complete OAuth flow first.",
            }

        try:
            service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
            profile = service.users().getProfile(userId="me").execute()
            return {
                "connected": True,
                "status": "ok",
                "email": profile.get("emailAddress"),
                "messages_total": profile.get("messagesTotal"),
                "threads_total": profile.get("threadsTotal"),
            }
        except HttpError as e:
            logger.error("Gmail API health check failed: %s", e)
            return {
                "connected": False,
                "status": "error",
                "message": f"Gmail API error: {e.resp.get('status')} {e.resp.get('reason')}",
            }
        except Exception as e:
            logger.error("Gmail API health check failed unexpectedly: %s", e)
            return {
                "connected": False,
                "status": "error",
                "message": str(e),
            }
