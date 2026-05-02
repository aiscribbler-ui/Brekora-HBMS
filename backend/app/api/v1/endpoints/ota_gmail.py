from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.config import get_settings
from app.schemas.gmail import (
    GmailAuthUrlResponse,
    GmailCallbackResponse,
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
    return {"auth_url": auth_url, "state": state}


@router.get("/callback", response_model=GmailCallbackResponse)
async def gmail_callback(
    code: str = Query(...),
    state: str | None = Query(None),
    service: GmailOAuthService = Depends(get_gmail_service),
) -> dict[str, Any]:
    """OAuth callback handler — exchanges code for tokens."""
    try:
        token_data = await service.exchange_code(code, state)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth token exchange failed: {exc}",
        ) from exc
    return {
        "status": "authenticated",
        "access_token": token_data["token"],
        "expires_at": token_data.get("expiry"),
    }
