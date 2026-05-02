import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import BookingStatus
from app.models.inventory_hold import InventoryHold
from app.models.payment import Payment
from app.services.inventory_service import InventoryService
from app.services.payment_service import PaymentService
from tests.test_payments import FakeRedis, _create_property, _create_room_type
from tests.test_razorpay_webhook import _create_booking_with_payment

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.mark.asyncio
async def test_payment_captured_confirms_booking(db_session: AsyncSession):
    """Webhook payment.captured confirms booking, captures payment, commits inventory."""
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)
    await db_session.commit()

    order_id = f"order_cap_{uuid.uuid4().hex[:8]}"
    booking, payment = await _create_booking_with_payment(
        db_session, prop.id, rt.id, order_id=order_id
    )

    fake_redis = FakeRedis()
    svc = PaymentService(db_session, DEFAULT_ORG_ID, fake_redis)

    payload = {
        "event": "payment.captured",
        "id": "evt_captured_1",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_123",
                    "order_id": order_id,
                }
            }
        },
    }
    result = await svc.process_webhook(payload, "")
    assert result is True

    await db_session.refresh(booking)
    await db_session.refresh(payment)
    assert booking.status == BookingStatus.confirmed.value
    assert payment.status == "captured"
    assert payment.provider_payment_id == "pay_123"

    hold_result = await db_session.execute(
        select(InventoryHold).where(InventoryHold.booking_id == booking.id)
    )
    hold = hold_result.scalar_one()
    assert hold.status == "committed"


@pytest.mark.asyncio
async def test_duplicate_webhook_idempotent(db_session: AsyncSession):
    """Processing the same webhook twice must not double-commit inventory."""
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)
    await db_session.commit()

    order_id = f"order_idem_{uuid.uuid4().hex[:8]}"
    booking, payment = await _create_booking_with_payment(
        db_session, prop.id, rt.id, order_id=order_id
    )

    fake_redis = FakeRedis()
    svc = PaymentService(db_session, DEFAULT_ORG_ID, fake_redis)

    payload = {
        "event": "payment.captured",
        "id": "evt_idempotent_1",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_789",
                    "order_id": order_id,
                }
            }
        },
    }
    result1 = await svc.process_webhook(payload, "")
    assert result1 is True

    result2 = await svc.process_webhook(payload, "")
    assert result2 is True

    await db_session.refresh(booking)
    assert booking.status == BookingStatus.confirmed.value

    hold_result = await db_session.execute(
        select(InventoryHold).where(InventoryHold.booking_id == booking.id)
    )
    hold = hold_result.scalar_one()
    assert hold.status == "committed"


@pytest.mark.asyncio
async def test_payment_captured_without_hold(db_session: AsyncSession):
    """Webhook payment.captured still confirms booking even if hold was already expired/released."""
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)
    await db_session.commit()

    order_id = f"order_nohold_{uuid.uuid4().hex[:8]}"
    booking, payment = await _create_booking_with_payment(
        db_session, prop.id, rt.id, order_id=order_id
    )

    # Release the hold to simulate expiry before payment capture
    inv_svc = InventoryService(db_session)
    hold_result = await db_session.execute(
        select(InventoryHold).where(InventoryHold.booking_id == booking.id)
    )
    hold = hold_result.scalar_one()
    await inv_svc.release_inventory(hold.id)
    await db_session.commit()

    fake_redis = FakeRedis()
    svc = PaymentService(db_session, DEFAULT_ORG_ID, fake_redis)

    payload = {
        "event": "payment.captured",
        "id": "evt_nohold_1",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_999",
                    "order_id": order_id,
                }
            }
        },
    }
    result = await svc.process_webhook(payload, "")
    assert result is True

    await db_session.refresh(booking)
    await db_session.refresh(payment)
    assert booking.status == BookingStatus.confirmed.value
    assert payment.status == "captured"
