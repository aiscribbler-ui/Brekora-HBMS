import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking, BookingStatus
from app.models.failed_payment import FailedPayment
from app.models.inventory_hold import InventoryHold
from app.models.payment import Payment
from app.services.payment_service import PaymentService
from tests.test_payments import FakeRedis, _create_property, _create_room_type
from tests.test_razorpay_webhook import _create_booking_with_payment

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.mark.asyncio
async def test_payment_failed_releases_inventory(db_session: AsyncSession):
    """Webhook payment.failed releases inventory and marks booking payment_failed."""
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)
    await db_session.commit()

    order_id = f"order_fail_{uuid.uuid4().hex[:8]}"
    booking, payment = await _create_booking_with_payment(
        db_session, prop.id, rt.id, order_id=order_id
    )

    fake_redis = FakeRedis()
    svc = PaymentService(db_session, DEFAULT_ORG_ID, fake_redis)

    payload = {
        "event": "payment.failed",
        "id": "evt_failed_1",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_456",
                    "order_id": order_id,
                    "error_description": "Payment declined by bank",
                }
            }
        },
    }
    result = await svc.process_webhook(payload, "")
    assert result is True

    await db_session.refresh(booking)
    await db_session.refresh(payment)
    assert booking.status == BookingStatus.payment_failed.value
    assert payment.status == "failed"

    hold_result = await db_session.execute(
        select(InventoryHold).where(InventoryHold.booking_id == booking.id)
    )
    hold = hold_result.scalar_one()
    assert hold.status == "released"

    fp_result = await db_session.execute(
        select(FailedPayment).where(FailedPayment.booking_id == booking.id)
    )
    fp = fp_result.scalar_one()
    assert fp.reason == "Payment declined by bank"
    assert fp.attempt_number == 1


@pytest.mark.asyncio
async def test_payment_timeout_detected(db_session: AsyncSession):
    """Old pending bookings without captured payment are timed out."""
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)
    await db_session.commit()

    order_id = f"order_timeout_{uuid.uuid4().hex[:8]}"
    booking, payment = await _create_booking_with_payment(
        db_session, prop.id, rt.id, order_id=order_id
    )

    # Age the booking so it appears overdue
    from sqlalchemy import update
    await db_session.execute(
        update(Booking)
        .where(Booking.id == booking.id)
        .values(created_at=datetime.now(timezone.utc) - timedelta(minutes=15))
    )
    await db_session.commit()

    fake_redis = FakeRedis()
    svc = PaymentService(db_session, DEFAULT_ORG_ID, fake_redis)
    timed_out = await svc.check_payment_timeouts()
    assert timed_out == 1

    await db_session.refresh(booking)
    assert booking.status == BookingStatus.payment_failed.value

    hold_result = await db_session.execute(
        select(InventoryHold).where(InventoryHold.booking_id == booking.id)
    )
    hold = hold_result.scalar_one()
    assert hold.status == "released"

    fp_result = await db_session.execute(
        select(FailedPayment).where(FailedPayment.booking_id == booking.id)
    )
    fp = fp_result.scalar_one()
    assert fp.reason == "timeout"
    assert fp.attempt_number == 1


@pytest.mark.asyncio
async def test_failed_payment_increment_attempt(db_session: AsyncSession):
    """Multiple failures for the same booking increment attempt_number."""
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)
    await db_session.commit()

    order_id = f"order_attempt_{uuid.uuid4().hex[:8]}"
    booking, payment = await _create_booking_with_payment(
        db_session, prop.id, rt.id, order_id=order_id
    )

    fake_redis = FakeRedis()
    svc = PaymentService(db_session, DEFAULT_ORG_ID, fake_redis)

    payload1 = {
        "event": "payment.failed",
        "id": "evt_attempt_1",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_001",
                    "order_id": order_id,
                    "error_description": "Card expired",
                }
            }
        },
    }
    result1 = await svc.process_webhook(payload1, "")
    assert result1 is True

    fp_result = await db_session.execute(
        select(FailedPayment)
        .where(FailedPayment.booking_id == booking.id)
        .order_by(FailedPayment.attempt_number)
    )
    fps = fp_result.scalars().all()
    assert len(fps) == 1
    assert fps[0].attempt_number == 1

    payload2 = {
        "event": "payment.failed",
        "id": "evt_attempt_2",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_002",
                    "order_id": order_id,
                    "error_description": "Insufficient funds",
                }
            }
        },
    }
    result2 = await svc.process_webhook(payload2, "")
    assert result2 is True

    fp_result2 = await db_session.execute(
        select(FailedPayment)
        .where(FailedPayment.booking_id == booking.id)
        .order_by(FailedPayment.attempt_number)
    )
    fps2 = fp_result2.scalars().all()
    assert len(fps2) == 2
    assert fps2[0].attempt_number == 1
    assert fps2[1].attempt_number == 2
    assert fps2[1].reason == "Insufficient funds"
