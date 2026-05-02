import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import BookingStatus
from app.models.parsed_booking import ParsedBookingQueue, ParsedBookingStatus
from app.models.property import Property
from app.models.room_type import RoomType
from app.repositories.parsed_booking_queue import ParsedBookingQueueRepository
from app.repositories.property import PropertyRepository
from app.repositories.room_type import RoomTypeRepository
from app.repositories.raw_email import RawEmailRepository
from app.services.ota_queue_service import OTAQueueService

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def _create_property_and_room(db_session: AsyncSession) -> tuple[Property, RoomType]:
    prop_repo = PropertyRepository(db_session, DEFAULT_ORG_ID)
    prop = await prop_repo.create({"name": "Queue Test Hotel"})

    rt_repo = RoomTypeRepository(db_session, DEFAULT_ORG_ID)
    rt = await rt_repo.create(
        {
            "property_id": prop.id,
            "name": "Deluxe",
            "count": 5,
            "base_capacity": 2,
            "max_capacity": 3,
            "default_rate": 100.00,
        }
    )
    return prop, rt


async def _create_raw_email(db_session: AsyncSession) -> uuid.UUID:
    repo = RawEmailRepository(db_session, DEFAULT_ORG_ID)
    email = await repo.create(
        {
            "gmail_message_id": f"msg_{uuid.uuid4().hex}",
            "ota_source": "airbnb",
            "subject": "Reservation confirmed",
            "sender": "no-reply@airbnb.com",
        }
    )
    return email.id


async def _create_queue_item(
    db_session: AsyncSession,
    raw_email_id: uuid.UUID | None = None,
    source_type: str = "airbnb",
    status: str = "pending",
    parsed_data: dict | None = None,
) -> ParsedBookingQueue:
    repo = ParsedBookingQueueRepository(db_session, DEFAULT_ORG_ID)
    data = {
        "source_type": source_type,
        "raw_email_id": raw_email_id,
        "ota_reference_id": f"REF-{uuid.uuid4().hex[:8]}",
        "parsed_data": parsed_data or {
            "ota_reference_id": "ABC123",
            "guest_name": "John Doe",
            "check_in": (date.today() + timedelta(days=5)).isoformat(),
            "check_out": (date.today() + timedelta(days=7)).isoformat(),
            "listing_id": "airbnb_123",
            "gross_amount": 2000.0,
        },
        "confidence_score": Decimal("0.92"),
        "status": status,
    }
    return await repo.create(data)


@pytest.mark.asyncio(loop_scope="session")
async def test_ota_queue_repository_methods(db_session: AsyncSession):
    raw_email_id = await _create_raw_email(db_session)
    item = await _create_queue_item(db_session, raw_email_id=raw_email_id)

    repo = ParsedBookingQueueRepository(db_session, DEFAULT_ORG_ID)

    # get_pending
    pending = await repo.get_pending()
    assert any(i.id == item.id for i in pending)

    # get_by_source_type
    by_source = await repo.get_by_source_type("airbnb")
    assert any(i.id == item.id for i in by_source)

    by_other = await repo.get_by_source_type("mmt")
    assert not any(i.id == item.id for i in by_other)

    # get_by_confidence_range
    in_range = await repo.get_by_confidence_range(Decimal("0.90"), Decimal("0.95"))
    assert any(i.id == item.id for i in in_range)

    out_of_range = await repo.get_by_confidence_range(Decimal("0.50"), Decimal("0.80"))
    assert not any(i.id == item.id for i in out_of_range)


@pytest.mark.asyncio(loop_scope="session")
async def test_ota_queue_service_list_and_details(db_session: AsyncSession):
    raw_email_id = await _create_raw_email(db_session)
    item = await _create_queue_item(db_session, raw_email_id=raw_email_id)

    svc = OTAQueueService(db_session, DEFAULT_ORG_ID)

    # list_pending
    results = await svc.list_pending()
    assert any(r.id == item.id for r in results)

    results = await svc.list_pending(source_type="airbnb")
    assert any(r.id == item.id for r in results)

    results = await svc.list_pending(source_type="mmt")
    assert not any(r.id == item.id for r in results)

    # get_details
    details = await svc.get_details(item.id)
    assert details is not None
    assert details["parsed_booking"].id == item.id
    assert details["raw_email"] is not None
    assert details["raw_email"].id == raw_email_id


@pytest.mark.asyncio(loop_scope="session")
async def test_ota_queue_service_edit(db_session: AsyncSession):
    item = await _create_queue_item(db_session)
    svc = OTAQueueService(db_session, DEFAULT_ORG_ID)

    from app.schemas.parsed_booking_queue import ParsedBookingQueueEditRequest

    edit_req = ParsedBookingQueueEditRequest(
        guest_name="Jane Doe",
        check_in=date.today() + timedelta(days=10),
        check_out=date.today() + timedelta(days=12),
        gross_amount=Decimal("3000.00"),
        review_notes="Updated guest info",
    )
    updated = await svc.edit(item.id, edit_req)
    assert updated.parsed_data["guest_name"] == "Jane Doe"
    assert updated.parsed_data["gross_amount"] == 3000.0
    assert updated.review_notes == "Updated guest info"


@pytest.mark.asyncio(loop_scope="session")
async def test_ota_queue_service_reject(db_session: AsyncSession):
    item = await _create_queue_item(db_session)
    svc = OTAQueueService(db_session, DEFAULT_ORG_ID)

    from app.schemas.parsed_booking_queue import ParsedBookingQueueRejectRequest

    reject_req = ParsedBookingQueueRejectRequest(rejection_reason="Duplicate booking")
    updated = await svc.reject(item.id, reject_req, manager_id=DEFAULT_ORG_ID)
    assert updated.status == ParsedBookingStatus.rejected.value
    assert updated.rejection_reason == "Duplicate booking"
    assert updated.manager_id == DEFAULT_ORG_ID


@pytest.mark.asyncio(loop_scope="session")
async def test_ota_queue_service_confirm_with_mapping(db_session: AsyncSession):
    prop, rt = await _create_property_and_room(db_session)

    # Create OTA mapping
    from app.repositories.ota_mapping import OTAMappingRepository
    ota_repo = OTAMappingRepository(db_session, DEFAULT_ORG_ID)
    await ota_repo.create(
        {
            "ota_source": "airbnb",
            "listing_id": "airbnb_123",
            "room_type_id": rt.id,
            "property_id": prop.id,
        }
    )

    raw_email_id = await _create_raw_email(db_session)
    item = await _create_queue_item(
        db_session,
        raw_email_id=raw_email_id,
        parsed_data={
            "ota_reference_id": "ABC123",
            "guest_name": "John Doe",
            "check_in": (date.today() + timedelta(days=20)).isoformat(),
            "check_out": (date.today() + timedelta(days=22)).isoformat(),
            "listing_id": "airbnb_123",
            "gross_amount": 2000.0,
        },
    )

    svc = OTAQueueService(db_session, DEFAULT_ORG_ID)

    from app.schemas.parsed_booking_queue import ParsedBookingQueueConfirmRequest

    confirm_req = ParsedBookingQueueConfirmRequest(
        check_in=date.today() + timedelta(days=20),
        check_out=date.today() + timedelta(days=22),
        gross_amount=Decimal("2000.00"),
        guest_name="John Doe",
    )
    booking = await svc.confirm(item.id, confirm_req, manager_id=DEFAULT_ORG_ID)
    assert booking.property_id == prop.id
    assert booking.status == BookingStatus.confirmed.value
    assert booking.source_type == "gmail_airbnb"

    # Verify queue item updated
    queue_repo = ParsedBookingQueueRepository(db_session, DEFAULT_ORG_ID)
    updated_item = await queue_repo.get(item.id)
    assert updated_item.status == ParsedBookingStatus.confirmed.value
    assert updated_item.confirmed_booking_id == booking.id
    assert updated_item.manager_id == DEFAULT_ORG_ID


@pytest.mark.asyncio(loop_scope="session")
async def test_ota_queue_service_confirm_with_explicit_ids(db_session: AsyncSession):
    prop, rt = await _create_property_and_room(db_session)
    item = await _create_queue_item(
        db_session,
        parsed_data={
            "ota_reference_id": "DEF456",
            "guest_name": "Alice Smith",
            "check_in": (date.today() + timedelta(days=30)).isoformat(),
            "check_out": (date.today() + timedelta(days=32)).isoformat(),
            "gross_amount": 1500.0,
        },
    )

    svc = OTAQueueService(db_session, DEFAULT_ORG_ID)

    from app.schemas.parsed_booking_queue import ParsedBookingQueueConfirmRequest

    confirm_req = ParsedBookingQueueConfirmRequest(
        property_id=prop.id,
        room_type_id=rt.id,
        check_in=date.today() + timedelta(days=30),
        check_out=date.today() + timedelta(days=32),
        gross_amount=Decimal("1500.00"),
    )
    booking = await svc.confirm(item.id, confirm_req, manager_id=DEFAULT_ORG_ID)
    assert booking.property_id == prop.id
    assert booking.status == BookingStatus.confirmed.value


@pytest.mark.asyncio(loop_scope="session")
async def test_ota_queue_service_confirm_insufficient_inventory(db_session: AsyncSession):
    from app.models.inventory_hold import InventoryHold
    from datetime import datetime, timezone

    prop_repo = PropertyRepository(db_session, DEFAULT_ORG_ID)
    prop = await prop_repo.create({"name": "No Room Hotel"})

    rt_repo = RoomTypeRepository(db_session, DEFAULT_ORG_ID)
    rt = await rt_repo.create(
        {
            "property_id": prop.id,
            "name": "Single",
            "count": 1,
            "base_capacity": 1,
            "max_capacity": 1,
            "default_rate": 100.00,
        }
    )

    # Consume the only room with an active hold
    hold = InventoryHold(
        org_id=DEFAULT_ORG_ID,
        booking_id=uuid.uuid4(),
        property_id=prop.id,
        room_type_id=rt.id,
        dates=[date.today() + timedelta(days=1)],
        status="active",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    db_session.add(hold)
    await db_session.flush()

    item = await _create_queue_item(
        db_session,
        parsed_data={
            "ota_reference_id": "GHI789",
            "guest_name": "Bob",
            "check_in": (date.today() + timedelta(days=1)).isoformat(),
            "check_out": (date.today() + timedelta(days=2)).isoformat(),
            "gross_amount": 500.0,
        },
    )

    svc = OTAQueueService(db_session, DEFAULT_ORG_ID)

    from app.schemas.parsed_booking_queue import ParsedBookingQueueConfirmRequest

    confirm_req = ParsedBookingQueueConfirmRequest(
        property_id=prop.id,
        room_type_id=rt.id,
        check_in=date.today() + timedelta(days=1),
        check_out=date.today() + timedelta(days=2),
        gross_amount=Decimal("500.00"),
    )
    with pytest.raises(ValueError, match="Insufficient inventory"):
        await svc.confirm(item.id, confirm_req, manager_id=DEFAULT_ORG_ID)


@pytest.mark.asyncio(loop_scope="session")
async def test_ota_queue_api_crud(client: AsyncClient, db_session: AsyncSession):
    # Create raw email and queue item via repository
    raw_email_id = await _create_raw_email(db_session)
    item = await _create_queue_item(db_session, raw_email_id=raw_email_id)

    # List endpoint
    resp = await client.get("/api/v1/ota/queue/")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(i["id"] == str(item.id) for i in data)

    # Filter by source_type
    resp = await client.get("/api/v1/ota/queue/?source_type=airbnb")
    assert resp.status_code == 200
    data = resp.json()
    assert any(i["id"] == str(item.id) for i in data)

    # Filter by status
    resp = await client.get("/api/v1/ota/queue/?status=pending")
    assert resp.status_code == 200
    data = resp.json()
    assert any(i["id"] == str(item.id) for i in data)

    # Filter by non-matching status
    resp = await client.get("/api/v1/ota/queue/?status=confirmed")
    assert resp.status_code == 200
    data = resp.json()
    assert not any(i["id"] == str(item.id) for i in data)


@pytest.mark.asyncio(loop_scope="session")
async def test_ota_queue_api_detail_and_actions(client: AsyncClient, db_session: AsyncSession):
    prop, rt = await _create_property_and_room(db_session)
    raw_email_id = await _create_raw_email(db_session)
    item = await _create_queue_item(
        db_session,
        raw_email_id=raw_email_id,
        parsed_data={
            "ota_reference_id": "API123",
            "guest_name": "API Guest",
            "check_in": (date.today() + timedelta(days=40)).isoformat(),
            "check_out": (date.today() + timedelta(days=42)).isoformat(),
            "listing_id": "airbnb_123",
            "gross_amount": 2500.0,
        },
    )

    # Create OTA mapping
    from app.repositories.ota_mapping import OTAMappingRepository
    ota_repo = OTAMappingRepository(db_session, DEFAULT_ORG_ID)
    await ota_repo.create(
        {
            "ota_source": "airbnb",
            "listing_id": "airbnb_123",
            "room_type_id": rt.id,
            "property_id": prop.id,
        }
    )

    # Detail
    resp = await client.get(f"/api/v1/ota/queue/{item.id}")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["parsed_booking"]["id"] == str(item.id)
    assert detail["raw_email"]["id"] == str(raw_email_id)
    assert detail["email_link"] is not None

    # Edit
    resp = await client.post(
        f"/api/v1/ota/queue/{item.id}/edit",
        json={
            "guest_name": "Edited Guest",
            "gross_amount": "3000.00",
            "review_notes": "Edited via API",
        },
    )
    assert resp.status_code == 200
    edited = resp.json()
    assert edited["parsed_data"]["guest_name"] == "Edited Guest"
    assert edited["review_notes"] == "Edited via API"

    # Reject
    resp = await client.post(
        f"/api/v1/ota/queue/{item.id}/reject",
        json={"rejection_reason": "Test rejection"},
    )
    assert resp.status_code == 200
    rejected = resp.json()
    assert rejected["status"] == "rejected"
    assert rejected["rejection_reason"] == "Test rejection"


@pytest.mark.asyncio(loop_scope="session")
async def test_ota_queue_api_confirm(client: AsyncClient, db_session: AsyncSession):
    prop, rt = await _create_property_and_room(db_session)
    raw_email_id = await _create_raw_email(db_session)
    item = await _create_queue_item(
        db_session,
        raw_email_id=raw_email_id,
        parsed_data={
            "ota_reference_id": "CNF456",
            "guest_name": "Confirm Guest",
            "check_in": (date.today() + timedelta(days=50)).isoformat(),
            "check_out": (date.today() + timedelta(days=52)).isoformat(),
            "listing_id": "airbnb_123",
            "gross_amount": 1800.0,
        },
    )

    # Create OTA mapping
    from app.repositories.ota_mapping import OTAMappingRepository
    ota_repo = OTAMappingRepository(db_session, DEFAULT_ORG_ID)
    await ota_repo.create(
        {
            "ota_source": "airbnb",
            "listing_id": "airbnb_123",
            "room_type_id": rt.id,
            "property_id": prop.id,
        }
    )

    resp = await client.post(
        f"/api/v1/ota/queue/{item.id}/confirm",
        json={
            "check_in": str(date.today() + timedelta(days=50)),
            "check_out": str(date.today() + timedelta(days=52)),
            "gross_amount": "1800.00",
        },
    )
    assert resp.status_code == 201
    result = resp.json()
    assert result["status"] == "confirmed"
    assert "booking_id" in result

    # Verify queue item is confirmed
    resp = await client.get(f"/api/v1/ota/queue/{item.id}")
    assert resp.status_code == 200
    assert resp.json()["parsed_booking"]["status"] == "confirmed"
    assert resp.json()["parsed_booking"]["confirmed_booking_id"] == result["booking_id"]
    assert resp.json()["email_link"] is not None
