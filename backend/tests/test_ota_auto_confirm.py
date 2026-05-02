"""Tests for OTA auto-confirm toggle and logic."""
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
from app.repositories.ota_mapping import OTAMappingRepository
from app.repositories.ota_settings import OTASettingsRepository
from app.repositories.parsed_booking_queue import ParsedBookingQueueRepository
from app.repositories.property import PropertyRepository
from app.repositories.raw_email import RawEmailRepository
from app.repositories.room_type import RoomTypeRepository
from app.services.ota_queue_service import OTAQueueService

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def _create_property_and_room(db_session: AsyncSession) -> tuple[Property, RoomType]:
    prop_repo = PropertyRepository(db_session, DEFAULT_ORG_ID)
    prop = await prop_repo.create({"name": "Auto Confirm Hotel"})

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


async def _create_raw_email(db_session: AsyncSession, ota_source: str = "airbnb") -> uuid.UUID:
    repo = RawEmailRepository(db_session, DEFAULT_ORG_ID)
    email = await repo.create(
        {
            "gmail_message_id": f"msg_{uuid.uuid4().hex}",
            "ota_source": ota_source,
            "subject": "Reservation confirmed",
            "sender": f"no-reply@{ota_source}.com",
        }
    )
    return email.id


async def _create_queue_item(
    db_session: AsyncSession,
    raw_email_id: uuid.UUID | None = None,
    source_type: str = "airbnb",
    confidence_score: Decimal = Decimal("0.96"),
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
        "confidence_score": confidence_score,
        "status": "pending",
    }
    return await repo.create(data)


async def _create_ota_settings(
    db_session: AsyncSession,
    ota_source: str = "airbnb",
    auto_confirm: bool = True,
    min_confidence: float = 0.95,
) -> None:
    repo = OTASettingsRepository(db_session, DEFAULT_ORG_ID)
    await repo.create(
        {
            "ota_source": ota_source,
            "auto_confirm": auto_confirm,
            "min_confidence": min_confidence,
        }
    )


async def _create_ota_mapping(
    db_session: AsyncSession,
    prop: Property,
    rt: RoomType,
    ota_source: str = "airbnb",
    listing_id: str = "airbnb_123",
) -> None:
    repo = OTAMappingRepository(db_session, DEFAULT_ORG_ID)
    await repo.create(
        {
            "ota_source": ota_source,
            "listing_id": listing_id,
            "room_type_id": rt.id,
            "property_id": prop.id,
        }
    )


@pytest.mark.asyncio(loop_scope="session")
async def test_auto_confirm_triggers_when_enabled_and_high_confidence(db_session: AsyncSession):
    prop, rt = await _create_property_and_room(db_session)
    await _create_ota_mapping(db_session, prop, rt)
    await _create_ota_settings(db_session, auto_confirm=True, min_confidence=0.95)
    raw_email_id = await _create_raw_email(db_session)
    item = await _create_queue_item(db_session, raw_email_id=raw_email_id, confidence_score=Decimal("0.98"))

    svc = OTAQueueService(db_session, DEFAULT_ORG_ID)
    booking = await svc.process_auto_confirm(item.id)

    assert booking is not None
    assert booking.status == BookingStatus.confirmed.value

    # Verify queue item updated
    queue_repo = ParsedBookingQueueRepository(db_session, DEFAULT_ORG_ID)
    updated = await queue_repo.get(item.id)
    assert updated.status == ParsedBookingStatus.confirmed.value
    assert updated.confirmed_booking_id == booking.id


@pytest.mark.asyncio(loop_scope="session")
async def test_auto_confirm_skipped_when_disabled(db_session: AsyncSession):
    prop, rt = await _create_property_and_room(db_session)
    await _create_ota_mapping(db_session, prop, rt)
    await _create_ota_settings(db_session, auto_confirm=False, min_confidence=0.95)
    raw_email_id = await _create_raw_email(db_session)
    item = await _create_queue_item(db_session, raw_email_id=raw_email_id, confidence_score=Decimal("0.98"))

    svc = OTAQueueService(db_session, DEFAULT_ORG_ID)
    booking = await svc.process_auto_confirm(item.id)

    assert booking is None

    queue_repo = ParsedBookingQueueRepository(db_session, DEFAULT_ORG_ID)
    updated = await queue_repo.get(item.id)
    assert updated.status == ParsedBookingStatus.pending.value


@pytest.mark.asyncio(loop_scope="session")
async def test_auto_confirm_skipped_when_confidence_below_threshold(db_session: AsyncSession):
    prop, rt = await _create_property_and_room(db_session)
    await _create_ota_mapping(db_session, prop, rt)
    await _create_ota_settings(db_session, auto_confirm=True, min_confidence=0.95)
    raw_email_id = await _create_raw_email(db_session)
    item = await _create_queue_item(db_session, raw_email_id=raw_email_id, confidence_score=Decimal("0.90"))

    svc = OTAQueueService(db_session, DEFAULT_ORG_ID)
    booking = await svc.process_auto_confirm(item.id)

    assert booking is None

    queue_repo = ParsedBookingQueueRepository(db_session, DEFAULT_ORG_ID)
    updated = await queue_repo.get(item.id)
    assert updated.status == ParsedBookingStatus.pending.value


@pytest.mark.asyncio(loop_scope="session")
async def test_auto_confirm_skipped_when_no_mapping_exists(db_session: AsyncSession):
    prop, rt = await _create_property_and_room(db_session)
    # No mapping created
    await _create_ota_settings(db_session, auto_confirm=True, min_confidence=0.95)
    raw_email_id = await _create_raw_email(db_session)
    item = await _create_queue_item(db_session, raw_email_id=raw_email_id, confidence_score=Decimal("0.98"))

    svc = OTAQueueService(db_session, DEFAULT_ORG_ID)
    booking = await svc.process_auto_confirm(item.id)

    assert booking is None

    queue_repo = ParsedBookingQueueRepository(db_session, DEFAULT_ORG_ID)
    updated = await queue_repo.get(item.id)
    assert updated.status == ParsedBookingStatus.pending.value


@pytest.mark.asyncio(loop_scope="session")
async def test_auto_confirm_skipped_when_no_settings(db_session: AsyncSession):
    prop, rt = await _create_property_and_room(db_session)
    await _create_ota_mapping(db_session, prop, rt)
    # No settings created
    raw_email_id = await _create_raw_email(db_session)
    item = await _create_queue_item(db_session, raw_email_id=raw_email_id, confidence_score=Decimal("0.98"))

    svc = OTAQueueService(db_session, DEFAULT_ORG_ID)
    booking = await svc.process_auto_confirm(item.id)

    assert booking is None

    queue_repo = ParsedBookingQueueRepository(db_session, DEFAULT_ORG_ID)
    updated = await queue_repo.get(item.id)
    assert updated.status == ParsedBookingStatus.pending.value


@pytest.mark.asyncio(loop_scope="session")
async def test_ota_settings_crud_api(client: AsyncClient, db_session: AsyncSession):
    # Create settings
    resp = await client.put(
        "/api/v1/ota/settings/",
        json={
            "ota_source": "airbnb",
            "auto_confirm": True,
            "min_confidence": 0.95,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ota_source"] == "airbnb"
    assert data["auto_confirm"] is True
    assert data["min_confidence"] == 0.95

    # List settings
    resp = await client.get("/api/v1/ota/settings/")
    assert resp.status_code == 200
    settings_list = resp.json()
    assert any(s["ota_source"] == "airbnb" for s in settings_list)

    # Update settings (upsert)
    resp = await client.put(
        "/api/v1/ota/settings/",
        json={
            "ota_source": "airbnb",
            "auto_confirm": False,
            "min_confidence": 0.90,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["auto_confirm"] is False
    assert data["min_confidence"] == 0.90

    # Create settings for another OTA
    resp = await client.put(
        "/api/v1/ota/settings/",
        json={
            "ota_source": "mmt",
            "auto_confirm": True,
            "min_confidence": 0.92,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ota_source"] == "mmt"

    # List again
    resp = await client.get("/api/v1/ota/settings/")
    assert resp.status_code == 200
    settings_list = resp.json()
    assert len(settings_list) == 2
