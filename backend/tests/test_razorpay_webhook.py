import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking, BookingStatus
from app.models.inventory_hold import InventoryHold
from app.models.payment import Payment
from app.models.property import Property
from app.models.room_type import RoomType
from app.services.inventory_service import InventoryService
from app.services.payment_service import PaymentService

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class FakeRedis:
    """Minimal fake Redis for idempotency tests."""

    def __init__(self):
        self._data = {}

    async def get(self, key):
        return self._data.get(key)

    async def setex(self, key, seconds, value):
        self._data[key] = value

    async def delete(self, key):
        if key in self._data:
            del self._data[key]
            return 1
        return 0


async def _create_property(session: AsyncSession) -> Property:
    prop = Property(
        org_id=DEFAULT_ORG_ID,
        name="Test Retreat",
        address="Dharamkot",
    )
    session.add(prop)
    await session.flush()
    await session.refresh(prop)
    return prop


async def _create_room_type(
    session: AsyncSession, property_id: uuid.UUID, count: int = 5
) -> RoomType:
    rt = RoomType(
        org_id=DEFAULT_ORG_ID,
        property_id=property_id,
        name="Deluxe Room",
        count=count,
        base_capacity=2,
        max_capacity=3,
        default_rate=Decimal("2500.00"),
    )
    session.add(rt)
    await session.flush()
    await session.refresh(rt)
    return rt


async def _create_booking_with_payment(
    session: AsyncSession,
    property_id: uuid.UUID,
    room_type_id: uuid.UUID,
    order_id: str | None = None,
) -> tuple[Booking, Payment]:
    check_in = date.today() + timedelta(days=7)
    check_out = check_in + timedelta(days=2)
    booking = Booking(
        org_id=DEFAULT_ORG_ID,
        booking_type="room",
        source_type="direct",
        property_id=property_id,
        check_in=check_in,
        check_out=check_out,
        status=BookingStatus.pending_payment.value,
        gross_amount=Decimal("5000.00"),
        discount_amount=Decimal("0.00"),
        tax_amount=Decimal("600.00"),
        total_amount=Decimal("5600.00"),
        currency="INR",
    )
    session.add(booking)
    await session.flush()
    await session.refresh(booking)

    inv_svc = InventoryService(session)
    await inv_svc.hold_inventory(
        booking_id=booking.id,
        property_id=property_id,
        room_type_id=room_type_id,
        dates=[check_in, check_in + timedelta(days=1)],
    )
    await session.commit()

    payment = Payment(
        org_id=DEFAULT_ORG_ID,
        booking_id=booking.id,
        amount=Decimal("5600.00"),
        currency="INR",
        provider="razorpay",
        provider_order_id=order_id or f"order_test_{booking.id}",
        status="created",
    )
    session.add(payment)
    await session.flush()
    await session.refresh(payment)
    await session.commit()
    return booking, payment


@pytest.mark.asyncio
async def test_webhook_signature_verification(db_session: AsyncSession, monkeypatch):
    """Invalid signature should not process event."""
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)
    await db_session.commit()

    order_id = f"order_sig_{uuid.uuid4().hex[:8]}"
    booking, payment = await _create_booking_with_payment(db_session, prop.id, rt.id, order_id=order_id)

    fake_redis = FakeRedis()
    svc = PaymentService(db_session, DEFAULT_ORG_ID, fake_redis)

    # Configure a webhook secret so verification is strict
    monkeypatch.setattr(
        "app.services.payment_service.get_settings",
        lambda: type("S", (), {"RAZORPAY_WEBHOOK_SECRET": "whsec_test_secret"})(),
    )

    payload = {
        "event": "payment.captured",
        "id": "evt_1",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_123",
                    "order_id": order_id,
                }
            }
        },
    }
    result = await svc.process_webhook(payload, "bad_signature")
    assert result is False

    # Booking should still be pending_payment
    await db_session.refresh(booking)
    assert booking.status == BookingStatus.pending_payment.value


@pytest.mark.asyncio
async def test_payment_captured_commits_inventory_and_confirms_booking(db_session: AsyncSession):
    """payment.captured webhook commits inventory and confirms booking."""
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)
    await db_session.commit()

    order_id = f"order_cap_{uuid.uuid4().hex[:8]}"
    booking, payment = await _create_booking_with_payment(db_session, prop.id, rt.id, order_id=order_id)

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

    # Hold should be committed
    hold_result = await db_session.execute(
        select(InventoryHold).where(InventoryHold.booking_id == booking.id)
    )
    hold = hold_result.scalar_one()
    assert hold.status == "committed"


@pytest.mark.asyncio
async def test_payment_failed_releases_inventory_and_marks_failed(db_session: AsyncSession):
    """payment.failed webhook releases inventory and marks booking payment_failed."""
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)
    await db_session.commit()

    order_id = f"order_fail_{uuid.uuid4().hex[:8]}"
    booking, payment = await _create_booking_with_payment(db_session, prop.id, rt.id, order_id=order_id)

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

    # Hold should be released
    hold_result = await db_session.execute(
        select(InventoryHold).where(InventoryHold.booking_id == booking.id)
    )
    hold = hold_result.scalar_one()
    assert hold.status == "released"


@pytest.mark.asyncio
async def test_webhook_idempotency(db_session: AsyncSession):
    """Same webhook processed twice does not double-commit inventory."""
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)
    await db_session.commit()

    order_id = f"order_idem_{uuid.uuid4().hex[:8]}"
    booking, payment = await _create_booking_with_payment(db_session, prop.id, rt.id, order_id=order_id)

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

    # Second time should return True because already processed
    result2 = await svc.process_webhook(payload, "")
    assert result2 is True

    await db_session.refresh(booking)
    assert booking.status == BookingStatus.confirmed.value

    # Verify hold is still committed (not double-committed)
    hold_result = await db_session.execute(
        select(InventoryHold).where(InventoryHold.booking_id == booking.id)
    )
    hold = hold_result.scalar_one()
    assert hold.status == "committed"
