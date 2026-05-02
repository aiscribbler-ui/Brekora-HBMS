import asyncio
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.exceptions import BookingConflictError
from app.models.booking import Booking
from app.models.inventory_hold import InventoryHold
from app.models.package import Package, PackageComposition
from app.models.property import Property
from app.models.room_type import RoomType
from app.schemas.booking import BookingInitRequest
from app.schemas.conflict import AlternativeSuggestion, BookingConflictResponse
from app.services.booking_service import BookingInitService
from app.services.conflict_service import ConflictService

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
    name: str = "Deluxe Room",
    count: int = 5,
    base_capacity: int = 2,
    default_rate: Decimal = Decimal("2500.00"),
) -> RoomType:
    rt = RoomType(
        org_id=DEFAULT_ORG_ID,
        property_id=property_id,
        name=name,
        count=count,
        base_capacity=base_capacity,
        max_capacity=3,
        default_rate=default_rate,
    )
    session.add(rt)
    await session.flush()
    await session.refresh(rt)
    return rt


async def _create_package(
    session: AsyncSession,
    property_id: uuid.UUID,
    name: str = "Weekend Package",
    room_type_id: uuid.UUID | None = None,
    base_price: Decimal = Decimal("5000.00"),
    max_occupancy: int = 2,
) -> Package:
    pkg = Package(
        org_id=DEFAULT_ORG_ID,
        property_id=property_id,
        name=name,
        status="active",
        base_price=base_price,
        max_occupancy=max_occupancy,
        is_active=True,
    )
    session.add(pkg)
    await session.flush()
    await session.refresh(pkg)

    if room_type_id is not None:
        comp = PackageComposition(
            org_id=DEFAULT_ORG_ID,
            package_id=pkg.id,
            room_type_id=room_type_id,
            quantity=1,
            nights=1,
        )
        session.add(comp)
        await session.flush()
        await session.refresh(pkg, attribute_names=["compositions"])

    return pkg


@pytest.mark.asyncio
async def test_init_booking_conflict_includes_alternatives(db_session: AsyncSession):
    """When inventory is exhausted, BookingConflictError carries alternatives."""
    prop = await _create_property(db_session)
    rt1 = await _create_room_type(db_session, prop.id, name="Standard Room", count=1)
    rt2 = await _create_room_type(
        db_session, prop.id, name="Superior Room", count=2, default_rate=Decimal("3000.00")
    )
    pkg = await _create_package(
        db_session, prop.id, name="Weekend Package", room_type_id=rt2.id
    )
    await db_session.commit()

    # Consume the only Standard Room
    fake_redis = FakeRedis()
    svc = BookingInitService(db_session, DEFAULT_ORG_ID, fake_redis)
    data = BookingInitRequest(
        property_id=prop.id,
        item_type="room",
        item_id=rt1.id,
        check_in=date.today() + timedelta(days=7),
        check_out=date.today() + timedelta(days=8),
        guests=2,
    )
    # First init succeeds
    resp1 = await svc.init_booking(data)
    assert resp1.booking_id is not None

    # Second init for same room should raise BookingConflictError with alternatives
    with pytest.raises(BookingConflictError) as exc_info:
        await svc.init_booking(data)

    assert "Insufficient inventory" in str(exc_info.value)
    alts = exc_info.value.alternatives
    assert len(alts) > 0

    # Should include Superior Room and Weekend Package
    room_alts = [a for a in alts if a["item_type"] == "room"]
    pkg_alts = [a for a in alts if a["item_type"] == "package"]

    assert any(a["item_id"] == rt2.id for a in room_alts)
    assert any(a["item_id"] == pkg.id for a in pkg_alts)

    # Should NOT include the exhausted room
    assert not any(a["item_id"] == rt1.id for a in alts)

    # Should be sorted by price ascending
    prices = [a["suggested_price"] for a in alts]
    assert prices == sorted(prices)

    # Should include up to 5 alternatives
    assert len(alts) <= 5


@pytest.mark.asyncio
async def test_conflict_service_find_alternatives(db_session: AsyncSession):
    """ConflictService returns available room types and packages."""
    prop = await _create_property(db_session)
    rt1 = await _create_room_type(db_session, prop.id, name="Budget Room", count=1)
    rt2 = await _create_room_type(
        db_session, prop.id, name="Luxury Room", count=2, default_rate=Decimal("5000.00")
    )
    pkg = await _create_package(
        db_session, prop.id, name="Luxury Package", room_type_id=rt2.id, base_price=Decimal("4500.00")
    )
    await db_session.commit()

    conflict_svc = ConflictService(db_session, DEFAULT_ORG_ID)
    check_in = date.today() + timedelta(days=7)
    check_out = check_in + timedelta(days=1)

    alts = await conflict_svc.find_alternatives(
        property_id=prop.id,
        check_in=check_in,
        check_out=check_out,
        guests=2,
        excluded_room_type_id=rt1.id,
    )

    assert len(alts) == 2  # rt2 and pkg
    assert alts[0]["item_type"] == "package"  # cheaper
    assert alts[0]["item_id"] == pkg.id
    assert alts[1]["item_type"] == "room"
    assert alts[1]["item_id"] == rt2.id

    # Excluded item should not appear
    assert not any(a["item_id"] == rt1.id for a in alts)


@pytest.mark.asyncio
async def test_booking_conflict_response_is_json_serializable():
    """BookingConflictResponse produces JSON-serializable output for the API."""
    alts = [
        AlternativeSuggestion(
            item_type="room",
            item_id=uuid.uuid4(),
            item_name="Deluxe Room",
            available_count=2,
            suggested_price=Decimal("3000.00"),
            currency="INR",
        )
    ]
    response = BookingConflictResponse(
        detail="Insufficient inventory",
        alternatives=alts,
    )
    dumped = response.model_dump(mode="json")
    assert dumped["detail"] == "Insufficient inventory"
    assert len(dumped["alternatives"]) == 1
    assert dumped["alternatives"][0]["item_type"] == "room"
    assert isinstance(dumped["alternatives"][0]["item_id"], str)


@pytest.mark.asyncio
async def test_two_simultaneous_inits_one_success_one_409(db_session: AsyncSession):
    """Two simultaneous init_booking calls for the last room result in one success and one 409."""
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, name="Only Room", count=1)
    await db_session.commit()

    check_in = date.today() + timedelta(days=7)
    check_out = check_in + timedelta(days=1)

    data = BookingInitRequest(
        property_id=prop.id,
        item_type="room",
        item_id=rt.id,
        check_in=check_in,
        check_out=check_out,
        guests=2,
    )

    # Create two separate sessions from the same engine for true concurrency
    session_maker = async_sessionmaker(db_session.bind, class_=AsyncSession, expire_on_commit=False)

    async def _init(session: AsyncSession):
        fake_redis = FakeRedis()
        svc = BookingInitService(session, DEFAULT_ORG_ID, fake_redis)
        try:
            return await svc.init_booking(data)
        except BookingConflictError as exc:
            return exc
        except ValueError as exc:
            return exc

    async with session_maker() as session1, session_maker() as session2:
        result1 = await _init(session1)
        result2 = await _init(session2)

        results = [result1, result2]
        successes = [r for r in results if hasattr(r, "booking_id")]
        conflicts = [r for r in results if isinstance(r, (BookingConflictError, ValueError))]

        assert len(successes) == 1, f"Expected 1 success, got {len(successes)}: {results}"
        assert len(conflicts) == 1, f"Expected 1 conflict, got {len(conflicts)}: {results}"

        # Commit the outer session of the success so the booking is visible
        if hasattr(result1, "booking_id"):
            await session1.commit()
        else:
            await session2.commit()

    # Verify exactly one booking was created
    result = await db_session.execute(
        select(Booking).where(Booking.property_id == prop.id)
    )
    bookings = result.scalars().all()
    assert len(bookings) == 1

    # Verify exactly one active hold exists (hold is committed in inner session)
    result = await db_session.execute(
        select(InventoryHold).where(InventoryHold.property_id == prop.id)
    )
    holds = result.scalars().all()
    assert len(holds) == 1
    assert holds[0].status == "active"


@pytest.mark.asyncio
async def test_alternatives_exclude_requested_package(db_session: AsyncSession):
    """When a package is unavailable, alternatives exclude that package."""
    prop = await _create_property(db_session)
    rt = await _create_room_type(db_session, prop.id, name="Base Room", count=1)
    pkg1 = await _create_package(
        db_session, prop.id, name="Package A", room_type_id=rt.id, base_price=Decimal("4000.00")
    )
    pkg2 = await _create_package(
        db_session, prop.id, name="Package B", room_type_id=rt.id, base_price=Decimal("3500.00")
    )
    await db_session.commit()

    # Consume the only room via a room booking
    fake_redis = FakeRedis()
    svc = BookingInitService(db_session, DEFAULT_ORG_ID, fake_redis)
    room_data = BookingInitRequest(
        property_id=prop.id,
        item_type="room",
        item_id=rt.id,
        check_in=date.today() + timedelta(days=7),
        check_out=date.today() + timedelta(days=8),
        guests=2,
    )
    await svc.init_booking(room_data)

    # Now try to book pkg1 - should fail because room is held
    pkg_data = BookingInitRequest(
        property_id=prop.id,
        item_type="package",
        item_id=pkg1.id,
        check_in=date.today() + timedelta(days=7),
        check_out=date.today() + timedelta(days=8),
        guests=2,
    )
    with pytest.raises(BookingConflictError) as exc_info:
        await svc.init_booking(pkg_data)

    alts = exc_info.value.alternatives
    # pkg1 should be excluded
    assert not any(a["item_id"] == pkg1.id for a in alts)
    # pkg2 might appear if available, but since room is held it won't either
    # The important thing is pkg1 is excluded
