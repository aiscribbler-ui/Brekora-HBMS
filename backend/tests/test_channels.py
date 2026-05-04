import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.ota_mapping import OTAMappingRepository
from app.repositories.property import PropertyRepository
from app.repositories.room_type import RoomTypeRepository
from app.services.channels import (
    CanonicalBooking,
    ChannelManagerStub,
    ChannelSource,
    DirectSource,
    GmailAirbnbSource,
    GmailGoibiboSource,
    GmailMMTSource,
    ICalSource,
    ManualSource,
)

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def make_parsed_result(**overrides) -> dict:
    base = {
        "ota_reference_id": "OTA-123",
        "guest_name": "Alice Smith",
        "guest_email": "alice@example.com",
        "check_in": date(2025, 6, 1),
        "check_out": date(2025, 6, 5),
        "listing_id": "airbnb_12345",
        "number_of_guests": 2,
        "gross_amount": 1000.0,
        "ota_commission": 150.0,
        "net_payout": 850.0,
        "special_requests": "Late check-in",
        "booking_date": date(2025, 5, 1),
        "confidence_scores": {},
        "overall_confidence": 0.95,
        "needs_manual_review": False,
        "review_reason": None,
        "raw_payload": {"original": "data"},
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 1. Adapter normalize() tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_direct_source_normalize():
    src = DirectSource()
    payload = {
        "property_id": uuid.uuid4(),
        "room_type_id": uuid.uuid4(),
        "guest_name": "Bob",
        "guest_email": "bob@example.com",
        "check_in": date(2025, 7, 1),
        "check_out": date(2025, 7, 3),
        "number_of_guests": 2,
        "gross_amount": Decimal("2000.00"),
        "total_amount": Decimal("2000.00"),
        "currency": "INR",
        "special_requests": "Ground floor",
    }
    cb = await src.normalize(payload)
    assert cb.source_type == "direct"
    assert cb.guest_name == "Bob"
    assert cb.check_in == date(2025, 7, 1)
    assert cb.total_amount == Decimal("2000.00")
    assert cb.metadata["channel"] == "direct_booking_site"


@pytest.mark.asyncio
async def test_manual_source_normalize():
    src = ManualSource()
    payload = {
        "property_id": uuid.uuid4(),
        "guest_name": "Manager Guest",
        "check_in": date(2025, 8, 1),
        "check_out": date(2025, 8, 2),
        "entered_by": "manager_01",
    }
    cb = await src.normalize(payload)
    assert cb.source_type == "manual"
    assert cb.metadata["entered_by"] == "manager_01"


@pytest.mark.asyncio
async def test_gmail_airbnb_source_normalize_without_mapping():
    src = GmailAirbnbSource()
    payload = {"parsed_result": make_parsed_result()}
    cb = await src.normalize(payload)
    assert cb.source_type == "gmail_airbnb"
    assert cb.source_reference == "OTA-123"
    assert cb.guest_name == "Alice Smith"
    assert cb.room_type_id is None  # no DB session provided
    assert cb.metadata["parser_confidence"] == 0.95


@pytest.mark.asyncio
async def test_gmail_mmt_source_normalize_without_mapping():
    src = GmailMMTSource()
    parsed = make_parsed_result(
        voucher_number="MMT-456",
        hotel_name="Taj",
        room_type_name="Deluxe",
    )
    payload = {"parsed_result": parsed}
    cb = await src.normalize(payload)
    assert cb.source_type == "gmail_mmt"
    assert cb.source_reference == "MMT-456"
    assert cb.metadata["hotel_name"] == "Taj"


@pytest.mark.asyncio
async def test_gmail_goibibo_source_normalize_without_mapping():
    src = GmailGoibiboSource()
    parsed = make_parsed_result(
        booking_reference="GIB-789",
        hotel_id="HOTEL-99",
        room_details="Deluxe Room",
    )
    payload = {"parsed_result": parsed}
    cb = await src.normalize(payload)
    assert cb.source_type == "gmail_goibibo"
    assert cb.source_reference == "GIB-789"
    assert cb.metadata["hotel_id"] == "HOTEL-99"


@pytest.mark.asyncio
async def test_ical_source_normalize():
    src = ICalSource()
    payload = {
        "uid": "ical-123",
        "dtstart": date(2025, 9, 1),
        "dtend": date(2025, 9, 3),
        "summary": "iCal Booking",
        "feed_url": "https://example.com/cal.ics",
    }
    cb = await src.normalize(payload)
    assert cb.source_type == "ical"
    assert cb.source_reference == "ical-123"
    assert cb.metadata["feed_url"] == "https://example.com/cal.ics"


@pytest.mark.asyncio
async def test_channel_manager_stub_normalize():
    src = ChannelManagerStub()
    cb = await src.normalize({"some": "data"})
    assert cb.source_type == "channel_manager"
    assert cb.metadata["channel"] == "channel_manager_stub"


# ---------------------------------------------------------------------------
# 2. Validation tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_validate_passes():
    src = DirectSource()
    cb = CanonicalBooking(
        source_type="direct",
        property_id=uuid.uuid4(),
        check_in=date(2025, 6, 1),
        check_out=date(2025, 6, 5),
    )
    assert await src.validate(cb) is True


@pytest.mark.asyncio
async def test_validate_fails_missing_property():
    src = DirectSource()
    cb = CanonicalBooking(
        source_type="direct",
        check_in=date(2025, 6, 1),
        check_out=date(2025, 6, 5),
    )
    assert await src.validate(cb) is False


@pytest.mark.asyncio
async def test_validate_fails_missing_dates():
    src = DirectSource()
    cb = CanonicalBooking(
        source_type="direct",
        property_id=uuid.uuid4(),
    )
    assert await src.validate(cb) is False


# ---------------------------------------------------------------------------
# 3. create_booking() stub tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_create_booking_stub_without_org_id():
    src = DirectSource()
    cb = CanonicalBooking(
        source_type="direct",
        property_id=uuid.uuid4(),
        room_type_id=uuid.uuid4(),
        check_in=date(2025, 6, 1),
        check_out=date(2025, 6, 5),
        total_amount=Decimal("1000.00"),
    )
    mock_session = MagicMock()
    booking = await src.create_booking(cb, mock_session)
    assert booking.source_type == "direct"
    assert booking.property_id == cb.property_id


@pytest.mark.asyncio
async def test_create_booking_with_org_id(db_session: AsyncSession):
    # Setup property
    prop_repo = PropertyRepository(db_session, DEFAULT_ORG_ID)
    prop = await prop_repo.create({"name": "Channel Test Hotel"})

    rt_repo = RoomTypeRepository(db_session, DEFAULT_ORG_ID)
    rt = await rt_repo.create(
        {
            "property_id": prop.id,
            "name": "Standard",
            "count": 5,
            "base_capacity": 2,
            "max_capacity": 3,
            "default_rate": 100.00,
        }
    )

    src = DirectSource()
    cb = CanonicalBooking(
        source_type="direct",
        property_id=prop.id,
        room_type_id=rt.id,
        check_in=date(2025, 6, 1),
        check_out=date(2025, 6, 3),
        total_amount=Decimal("200.00"),
        metadata={"org_id": DEFAULT_ORG_ID},
    )

    booking = await src.create_booking(cb, db_session)
    assert booking.id is not None
    assert booking.org_id == DEFAULT_ORG_ID
    assert booking.property_id == prop.id


# ---------------------------------------------------------------------------
# 4. OTAMapping resolution tests for Gmail sources
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_gmail_airbnb_resolves_mapping(db_session: AsyncSession):
    prop_repo = PropertyRepository(db_session, DEFAULT_ORG_ID)
    prop = await prop_repo.create({"name": "Airbnb Map Hotel"})

    rt_repo = RoomTypeRepository(db_session, DEFAULT_ORG_ID)
    rt = await rt_repo.create(
        {
            "property_id": prop.id,
            "name": "Airbnb Room",
            "count": 3,
            "base_capacity": 2,
            "max_capacity": 4,
            "default_rate": 120.00,
        }
    )

    ota_repo = OTAMappingRepository(db_session, DEFAULT_ORG_ID)
    await ota_repo.create(
        {
            "ota_source": "gmail_airbnb",
            "listing_id": "airbnb_12345",
            "room_type_id": rt.id,
            "property_id": prop.id,
        }
    )

    src = GmailAirbnbSource()
    payload = {
        "parsed_result": make_parsed_result(),
        "db_session": db_session,
        "org_id": DEFAULT_ORG_ID,
    }
    cb = await src.normalize(payload)
    assert cb.room_type_id == rt.id
    assert cb.property_id == prop.id


@pytest.mark.asyncio
async def test_gmail_mmt_resolves_mapping(db_session: AsyncSession):
    prop_repo = PropertyRepository(db_session, DEFAULT_ORG_ID)
    prop = await prop_repo.create({"name": "MMT Map Hotel"})

    rt_repo = RoomTypeRepository(db_session, DEFAULT_ORG_ID)
    rt = await rt_repo.create(
        {
            "property_id": prop.id,
            "name": "MMT Room",
            "count": 2,
            "base_capacity": 2,
            "max_capacity": 2,
            "default_rate": 150.00,
        }
    )

    ota_repo = OTAMappingRepository(db_session, DEFAULT_ORG_ID)
    await ota_repo.create(
        {
            "ota_source": "gmail_mmt",
            "listing_id": "Taj:Deluxe",
            "room_type_id": rt.id,
            "property_id": prop.id,
        }
    )

    src = GmailMMTSource()
    payload = {
        "parsed_result": make_parsed_result(
            voucher_number="MMT-456",
            hotel_name="Taj",
            room_type_name="Deluxe",
        ),
        "db_session": db_session,
        "org_id": DEFAULT_ORG_ID,
    }
    cb = await src.normalize(payload)
    assert cb.room_type_id == rt.id
    assert cb.property_id == prop.id


@pytest.mark.asyncio
async def test_gmail_goibibo_resolves_mapping(db_session: AsyncSession):
    prop_repo = PropertyRepository(db_session, DEFAULT_ORG_ID)
    prop = await prop_repo.create({"name": "Goibibo Map Hotel"})

    rt_repo = RoomTypeRepository(db_session, DEFAULT_ORG_ID)
    rt = await rt_repo.create(
        {
            "property_id": prop.id,
            "name": "Goibibo Room",
            "count": 4,
            "base_capacity": 2,
            "max_capacity": 3,
            "default_rate": 130.00,
        }
    )

    ota_repo = OTAMappingRepository(db_session, DEFAULT_ORG_ID)
    await ota_repo.create(
        {
            "ota_source": "gmail_goibibo",
            "listing_id": "HOTEL-99+Deluxe Room",
            "room_type_id": rt.id,
            "property_id": prop.id,
        }
    )

    src = GmailGoibiboSource()
    payload = {
        "parsed_result": make_parsed_result(
            booking_reference="GIB-789",
            hotel_id="HOTEL-99",
            room_details="Deluxe Room",
        ),
        "db_session": db_session,
        "org_id": DEFAULT_ORG_ID,
    }
    cb = await src.normalize(payload)
    assert cb.room_type_id == rt.id
    assert cb.property_id == prop.id


# ---------------------------------------------------------------------------
# 5. source_type attribute tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_source_type_attributes():
    assert DirectSource.source_type == "direct"
    assert ManualSource.source_type == "manual"
    assert GmailAirbnbSource.source_type == "gmail_airbnb"
    assert GmailMMTSource.source_type == "gmail_mmt"
    assert GmailGoibiboSource.source_type == "gmail_goibibo"
    assert ICalSource.source_type == "ical"
    assert ChannelManagerStub.source_type == "channel_manager"


# ---------------------------------------------------------------------------
# 6. CanonicalBooking helper tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_canonical_to_booking_create():
    cb = CanonicalBooking(
        source_type="direct",
        property_id=uuid.uuid4(),
        check_in=date(2025, 6, 1),
        check_out=date(2025, 6, 5),
        total_amount=Decimal("1000.00"),
        currency="USD",
        guest_name="Test Guest",
    )
    data = cb.to_booking_create()
    assert data["booking_type"] == "room"
    assert data["source_type"] == "direct"
    assert data["currency"] == "USD"
    assert "guest_name" not in data  # not part of BookingCreate


@pytest.mark.asyncio
async def test_canonical_to_line_items():
    rt_id = uuid.uuid4()
    cb = CanonicalBooking(
        source_type="direct",
        room_type_id=rt_id,
        check_in=date(2025, 6, 1),
        check_out=date(2025, 6, 5),
        total_amount=Decimal("1000.00"),
    )
    items = cb.to_line_items()
    assert len(items) == 1
    assert items[0]["item_type"] == "room"
    assert items[0]["item_id"] == rt_id
    assert items[0]["nights"] == 4
    assert items[0]["total_price"] == Decimal("1000.00")


@pytest.mark.asyncio
async def test_canonical_to_line_items_no_room_type():
    cb = CanonicalBooking(
        source_type="direct",
        check_in=date(2025, 6, 1),
        check_out=date(2025, 6, 5),
    )
    items = cb.to_line_items()
    assert items == []


@pytest.mark.asyncio
async def test_canonical_to_line_items_zero_nights():
    rt_id = uuid.uuid4()
    cb = CanonicalBooking(
        source_type="direct",
        room_type_id=rt_id,
        check_in=date(2025, 6, 5),
        check_out=date(2025, 6, 5),  # same day
        total_amount=Decimal("500.00"),
    )
    items = cb.to_line_items()
    assert items[0]["nights"] == 1  # minimum 1 night
