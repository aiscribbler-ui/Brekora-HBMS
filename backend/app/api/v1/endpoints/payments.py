import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis_client
from app.db.session import get_db
from app.schemas.payment import OrderCreateRequest, OrderCreateResponse
from app.services.payment_service import PaymentService

router = APIRouter()

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def get_org_id(
    x_org_id: str | None = Header(default=None, alias="X-Org-ID"),
) -> uuid.UUID:
    if x_org_id:
        return uuid.UUID(x_org_id)
    return DEFAULT_ORG_ID


@router.post("/create-order", response_model=OrderCreateResponse, status_code=201)
async def create_order(
    data: OrderCreateRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
    org_id: uuid.UUID = Depends(get_org_id),
) -> OrderCreateResponse:
    svc = PaymentService(db, org_id, redis_client)
    try:
        order = await svc.create_order(data.booking_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    return OrderCreateResponse(
        order_id=order["id"],
        amount=order["amount"],
        currency=order["currency"],
        status=order["status"],
    )
