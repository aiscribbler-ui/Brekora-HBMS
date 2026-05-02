from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.core.config import get_settings


class GoogleOAuthService:
    @staticmethod
    def verify_token(id_token_str: str) -> dict:
        settings = get_settings()
        request = google_requests.Request()
        try:
            payload = id_token.verify_oauth2_token(
                id_token_str,
                request,
                audience=settings.GOOGLE_CLIENT_ID or None,
                clock_skew_in_seconds=10,
            )
        except Exception as exc:
            raise ValueError(f"Invalid Google ID token: {exc}") from exc

        if payload.get("iss") not in (
            "https://accounts.google.com",
            "accounts.google.com",
        ):
            raise ValueError("Invalid token issuer")

        return {
            "sub": payload.get("sub"),
            "email": payload.get("email"),
            "name": payload.get("name"),
            "picture": payload.get("picture"),
        }
