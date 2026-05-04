import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import BookingConflictError
from app.models.booking import Booking, BookingStatus
from app.models.inventory_hold import InventoryHold
from app.models.property import Property
from app.models.room_type import RoomType
from app.repositories.booking import BookingRepository
from app.schemas.booking import BookingInitRequest
from app.services.booking_modification_service import BookingModificationService
from app.services.booking_service import BookingInitService
from app.services.inventory_service import InventoryService

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class FakeRedis:
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
    session: AsyncSession,
    property_id: uuid.UUID,
    count: int = 5,
    name: str = "Deluxe Room",
    default_rate: Decimal = Decimal("2500.00"),
) -> RoomType:
    rt = RoomType(
        org_id=DEFAULT_ORG_ID,
        property_id=property_id,
        name=name,
        count=count,
        base_capacity=2,
        max_capacity=3,
        default_rate=default_rate,
    )
    session.add(rt)
    await session.flush()
    await session.refresh(rt)
    return rt


async def _create_confirmed_booking(
    session: AsyncSession,
    property_id: uuid.UUID,
    room_type_id: uuid.UUID,
    check_in: date,
    check_out: date,
    guests: int = 2,
) -> Booking:
    fake_redis = FakeRedis()
    svc = BookingInitService(session, DEFAULT_ORG_ID, fake_redis)

    data = BookingInitRequest(
        property_id=property_id,
        item_type="room",
        item_id=room_type_id,
        check_in=check_in,
        check_out=check_out,
        guests=guests,
    )
    resp = await svc.init_booking(data)
    booking_id = resp.booking_id
    hold_id = resp.hold_id

    # Commit so the inner serializable session in commit_inventory can see the booking
    await session.commit()

    inv_svc = InventoryService(session, fake_redis)
    await inv_svc.commit_inventory(hold_id)

    booking_repo = BookingRepository(session, DEFAULT_ORG_ID)
    booking = await booking_repo.get(booking_id)
    await booking_repo.update(booking, {"status": BookingStatus.confirmed.value})

    return booking


@pytest.mark.asyncio
async def test_modify_dates_success(db_session: AsyncSession):
    """Change check_out; verify repricing, inventory released and re-held."""
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)
    await db_session.commit()

    check_in = date.today() + timedelta(days=7)
    check_out = check_in + timedelta(days=2)
    booking = await _create_confirmed_booking(
        db_session, prop.id, rt.id, check_in, check_out
    )
    old_total = booking.total_amount

    # Find original hold
    holds_result = await db_session.execute(
        select(InventoryHold).where(
            InventoryHold.booking_id == booking.id,
            InventoryHold.status == "committed",
        )
    )
    original_holds = holds_result.scalars().all()
    assert len(original_holds) == 1
    original_hold_id = original_holds[0].id

    svc = BookingModificationService(db_session, DEFAULT_ORG_ID)
    new_check_out = check_out + timedelta(days=1)
    result = await svc.modify_booking(
        booking.id,
        {"check_out": new_check_out},
    )

    assert result["new_total"] > old_total
    assert result["payment_difference"] > 0
    assert booking.check_out == new_check_out

    # Original hold should be released
    await db_session.refresh(original_holds[0])
    assert original_holds[0].status == "released"

    # New committed hold should exist
    new_holds_result = await db_session.execute(
        select(InventoryHold).where(
            InventoryHold.booking_id == booking.id,
            InventoryHold.status == "committed",
        )
    )
    new_holds = new_holds_result.scalars().all()
    assert len(new_holds) == 1
    assert new_holds[0].id != original_hold_id


@pytest.mark.asyncio
async def test_modify_within_24h_blocked(db_session: AsyncSession):
    """Modifications within 24h of check-in are blocked."""
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)
    await db_session.commit()

    check_in = date.today()
    check_out = check_in + timedelta(days=1)
    booking = await _create_confirmed_booking(
        db_session, prop.id, rt.id, check_in, check_out
    )

    svc = BookingModificationService(db_session, DEFAULT_ORG_ID)
    with pytest.raises(ValueError, match="blocked within 24 hours"):
        await svc.modify_booking(
            booking.id,
            {"check_out": check_out + timedelta(days=1)},
        )


@pytest.mark.asyncio
async def test_modify_payment_difference_positive(db_session: AsyncSession):
    """Extending stay creates a positive difference and a Razorpay order."""
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)
    await db_session.commit()

    check_in = date.today() + timedelta(days=7)
    check_out = check_in + timedelta(days=2)
    booking = await _create_confirmed_booking(
        db_session, prop.id, rt.id, check_in, check_out
    )
    old_total = booking.total_amount

    svc = BookingModificationService(db_session, DEFAULT_ORG_ID)
    new_check_out = check_out + timedelta(days=1)
    result = await svc.modify_booking(
        booking.id,
        {"check_out": new_check_out},
    )

    assert result["payment_difference"] > 0
    assert result["new_total"] == old_total + result["payment_difference"]
    assert result["razorpay_order"] is not None
    assert result["razorpay_order"]["id"].startswith("order_stub_modification_")
    assert result["refund_amount"] is None


@pytest.mark.asyncio
async def test_modify_payment_difference_negative(db_session: AsyncSession):
    """Shortening stay creates a negative difference and a refund amount."""
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)
    await db_session.commit()

    check_in = date.today() + timedelta(days=7)
    check_out = check_in + timedelta(days=3)
    booking = await _create_confirmed_booking(
        db_session, prop.id, rt.id, check_in, check_out
    )
    old_total = booking.total_amount

    svc = BookingModificationService(db_session, DEFAULT_ORG_ID)
    new_check_out = check_out - timedelta(days=1)
    result = await svc.modify_booking(
        booking.id,
        {"check_out": new_check_out},
    )

    assert result["payment_difference"] < 0
    assert result["new_total"] == old_total + result["payment_difference"]
    assert result["refund_amount"] is not None
    assert result["refund_amount"] > 0
    assert result["razorpay_order"] is None


@pytest.mark.asyncio
async def test_modify_audit_log_created(db_session: AsyncSession):
    """Modification creates an audit entry in modification_log JSONB."""
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, count=5)
    await db_session.commit()

    check_in = date.today() + timedelta(days=7)
    check_out = check_in + timedelta(days=2)
    booking = await _create_confirmed_booking(
        db_session, prop.id, rt.id, check_in, check_out
    )

    svc = BookingModificationService(db_session, DEFAULT_ORG_ID)
    new_check_out = check_out + timedelta(days=1)
    await svc.modify_booking(
        booking.id,
        {"check_out": new_check_out, "reason": "Guest request"},
    )

    log = booking.modification_log
    assert log is not None
    assert len(log) == 1
    entry = log[0]
    assert entry["reason"] == "Guest request"
    assert "changes" in entry
    assert "check_out" in entry["changes"]
    assert entry["changes"]["check_out"]["old"] == str(check_out)
    assert entry["changes"]["check_out"]["new"] == str(new_check_out)
    assert "timestamp" in entry


@pytest.mark.asyncio
async def test_modify_insufficient_inventory(db_session: AsyncSession):
    """Modification to unavailable dates raises BookingConflictError with alternatives."""
    prop = await _create_property(db_session)
    rt1 = await _create_room_type(db_session, prop.id, count=1, name="Deluxe")
    rt2 = await _create_room_type(db_session, prop.id, count=5, name="Standard")
    await db_session.commit()

    check_in = date.today() + timedelta(days=7)
    check_out = check_in + timedelta(days=1)

    # First confirmed booking consumes the only Deluxe room
    booking1 = await _create_confirmed_booking(
        db_session, prop.id, rt1.id, check_in, check_out
    )

    # Second confirmed booking also consumes the room on different dates
    check_in_b = date.today() + timedelta(days=10)
    check_out_b = check_in_b + timedelta(days=1)
    await _create_confirmed_booking(
        db_session, prop.id, rt1.id, check_in_b, check_out_b
    )

    svc = BookingModificationService(db_session, DEFAULT_ORG_ID)
    with pytest.raises(BookingConflictError) as exc_info:
        await svc.modify_booking(
            booking1.id,
            {"check_in": check_in_b, "check_out": check_out_b},
        )

    assert "Insufficient inventory" in str(exc_info.value)
    assert len(exc_info.value.alternatives) > 0
    # Standard room should be suggested as alternative
    alt_ids = {alt["item_id"] for alt in exc_info.value.alternatives}
    assert rt2.id in alt_ids
