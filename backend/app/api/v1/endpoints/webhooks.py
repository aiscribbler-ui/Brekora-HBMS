import logging

from fastapi import APIRouter, Depends, Header, Request, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis_client
from app.db.session import get_db
from app.services.payment_service import PaymentService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
    x_razorpay_signature: str | None = Header(default=None, alias="X-Razorpay-Signature"),
) -> Response:
    """Razorpay webhook handler.

    Always returns 200 OK to prevent Razorpay retries, even on errors.
    """
    body = await request.body()
    try:
        payload = await request.json()
    except Exception as exc:
        logger.error("Invalid JSON in Razorpay webhook: %s", exc)
        return Response(status_code=status.HTTP_200_OK)

    # Determine org_id from payload notes if available, otherwise use default
    org_id = None
    try:
        notes = payload.get("payload", {}).get("order", {}).get("entity", {}).get("notes", {})
        org_id_str = notes.get("org_id")
        if org_id_str:
            import uuid
            org_id = uuid.UUID(org_id_str)
    except Exception:
        pass

    if org_id is None:
        import uuid
        org_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    svc = PaymentService(db, org_id, redis_client)
    try:
        await svc.process_webhook(payload, x_razorpay_signature or "")
    except Exception as exc:
        logger.error("Error processing Razorpay webhook: %s", exc)

    return Response(status_code=status.HTTP_200_OK)
