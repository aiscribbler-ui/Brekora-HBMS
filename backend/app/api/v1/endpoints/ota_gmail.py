from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.core.config import get_settings
from app.schemas.gmail import (
    GmailAuthUrlResponse,
    GmailStatusResponse,
)
from app.services.gmail_oauth_service import GmailOAuthService

router = APIRouter()
settings = get_settings()


def get_gmail_service() -> GmailOAuthService:
    return GmailOAuthService(settings)


@router.get("/status", response_model=GmailStatusResponse)
async def gmail_status(
    service: GmailOAuthService = Depends(get_gmail_service),
) -> dict[str, Any]:
    """Health check for Gmail API OAuth connection."""
    return await service.health_check()


@router.get("/auth", response_model=GmailAuthUrlResponse)
async def gmail_auth(
    service: GmailOAuthService = Depends(get_gmail_service),
) -> dict[str, str]:
    """Initiate Gmail OAuth 2.0 flow and return the authorization URL."""
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gmail OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        )
    auth_url, state = service.create_auth_url()
    await service.store_state(state)
    return {"auth_url": auth_url, "state": state}


def _build_callback_html(success: bool, message: str) -> str:
    """Return an HTML page that signals the parent window via postMessage."""
    event_type = "GMAIL_AUTH_SUCCESS" if success else "GMAIL_AUTH_ERROR"
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Gmail OAuth</title></head>
<body>
<script>
(function() {{
  if (window.opener) {{
    window.opener.postMessage({{ type: "{event_type}", message: "{message}" }}, "*");
  }}
  setTimeout(function() {{ window.close(); }}, 300);
}})();
</script>
<p>{"Connected successfully." if success else message}</p>
</body>
</html>"""


@router.get("/callback")
async def gmail_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
    service: GmailOAuthService = Depends(get_gmail_service),
) -> Response:
    """OAuth callback handler — exchanges code for tokens and returns HTML."""

    # Handle explicit errors from Google (e.g. user clicked Cancel)
    if error:
        msg = error_description or error
        return Response(
            content=_build_callback_html(success=False, message=msg),
            media_type="text/html",
        )

    if not code:
        return Response(
            content=_build_callback_html(
                success=False, message="Missing authorization code from Google."
            ),
            media_type="text/html",
        )

    # Verify CSRF state
    state_ok = await service.verify_state(state)
    if not state_ok:
        return Response(
            content=_build_callback_html(
                success=False, message="Invalid or expired OAuth state. Please try again."
            ),
            media_type="text/html",
        )

    try:
        await service.exchange_code(code, state)
    except Exception as exc:
        return Response(
            content=_build_callback_html(
                success=False, message=f"OAuth token exchange failed: {exc}"
            ),
            media_type="text/html",
        )

    return Response(
        content=_build_callback_html(success=True, message="Gmail connected successfully."),
        media_type="text/html",
    )


@router.post("/disconnect", status_code=204)
async def gmail_disconnect(
    service: GmailOAuthService = Depends(get_gmail_service),
) -> None:
    """Remove stored Gmail OAuth tokens."""
    await service.disconnect()
