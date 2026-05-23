import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.gmail import (
    GmailAuthUrlResponse,
    GmailStatusResponse,
)
from app.services.gmail_config_service import GmailConfigService
from app.services.gmail_oauth_service import GmailOAuthService

router = APIRouter()
settings = get_settings()
DEFAULT_ORG_ID = settings.DEFAULT_ORG_ID if hasattr(settings, "DEFAULT_ORG_ID") else None


def get_org_id(x_org_id: str | None = Header(default=None, alias="X-Org-ID")) -> uuid.UUID:
    if x_org_id:
        return uuid.UUID(x_org_id)
    if DEFAULT_ORG_ID:
        return DEFAULT_ORG_ID
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


class GmailConfigUpdate(BaseModel):
    client_id: str
    client_secret: str
    redirect_uri: str | None = None


async def get_gmail_service(
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> GmailOAuthService:
    config_svc = GmailConfigService(
        db, org_id, settings.GOOGLE_CLIENT_ID or "", settings.GOOGLE_CLIENT_SECRET or "", settings.GOOGLE_REDIRECT_URI or ""
    )
    return GmailOAuthService(settings, config_svc)


@router.get("/status", response_model=GmailStatusResponse)
async def gmail_status(
    service: GmailOAuthService = Depends(get_gmail_service),
) -> dict[str, Any]:
    """Health check for Gmail API OAuth connection."""
    return await service.health_check()


@router.get("/auth", response_model=GmailAuthUrlResponse)
async def gmail_auth(
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
    service: GmailOAuthService = Depends(get_gmail_service),
) -> dict[str, str]:
    """Initiate Gmail OAuth 2.0 flow and return the authorization URL."""
    config_svc = GmailConfigService(
        db, org_id, settings.GOOGLE_CLIENT_ID or "", settings.GOOGLE_CLIENT_SECRET or "", settings.GOOGLE_REDIRECT_URI or ""
    )
    configured = await config_svc.is_configured()
    if not configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gmail OAuth is not configured. Set client ID and secret in OTA settings first.",
        )
    auth_url, generated_state = await service.create_auth_url()
    await service.store_state(generated_state)
    return {"auth_url": auth_url, "state": generated_state}


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


@router.get("/config")
async def get_gmail_config(
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> dict[str, str | None]:
    """Return configured Gmail OAuth client ID (secret is masked)."""
    config_svc = GmailConfigService(
        db, org_id, settings.GOOGLE_CLIENT_ID or "", settings.GOOGLE_CLIENT_SECRET or "", settings.GOOGLE_REDIRECT_URI or ""
    )
    creds = await config_svc.get_credentials()
    client_secret = creds.get("client_secret")
    redirect_uri = await config_svc.get_redirect_uri()
    return {
        "client_id": creds.get("client_id"),
        "client_secret": ("*" * len(client_secret)) if client_secret else None,
        "configured": bool(creds.get("client_id") and creds.get("client_secret")),
        "redirect_uri": redirect_uri,
    }


@router.patch("/config")
async def update_gmail_config(
    data: GmailConfigUpdate,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_org_id),
) -> dict[str, Any]:
    """Store Gmail OAuth client credentials in system_config."""
    config_svc = GmailConfigService(
        db, org_id, settings.GOOGLE_CLIENT_ID or "", settings.GOOGLE_CLIENT_SECRET or "", settings.GOOGLE_REDIRECT_URI or ""
    )
    await config_svc.set_credentials(data.client_id, data.client_secret)
    if data.redirect_uri:
        await config_svc.set_redirect_uri(data.redirect_uri)
    return {"status": "saved", "configured": True}
