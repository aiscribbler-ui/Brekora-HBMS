import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking, BookingLineItem, BookingStatus
from app.models.property import Property
from app.models.user import User
from app.repositories.booking import BookingRepository
from app.repositories.property import PropertyRepository
from app.repositories.user import UserRepository

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def _create_property(db_session: AsyncSession) -> Property:
    repo = PropertyRepository(db_session, DEFAULT_ORG_ID)
    return await repo.create({"name": "Test Hotel"})


async def _create_guest(db_session: AsyncSession) -> User:
    repo = UserRepository(db_session, DEFAULT_ORG_ID)
    return await repo.create(
        {
            "email": f"guest_{uuid.uuid4().hex}@example.com",
            "password_hash": "hash",
            "first_name": "Guest",
            "last_name": "User",
        }
    )


@pytest.mark.asyncio
async def test_booking_repository_crud(db_session: AsyncSession):
    prop = await _create_property(db_session)
    guest = await _create_guest(db_session)
    repo = BookingRepository(db_session, DEFAULT_ORG_ID)

    # Create
    booking = await repo.create_with_line_items(
        {
            "booking_type": "room",
            "property_id": prop.id,
            "guest_id": guest.id,
            "check_in": date.today(),
            "check_out": date.today() + timedelta(days=2),
            "status": BookingStatus.pending_payment.value,
            "gross_amount": Decimal("1000.00"),
            "total_amount": Decimal("1000.00"),
        },
        line_items=[
            {
                "item_type": "room",
                "item_id": uuid.uuid4(),
                "quantity": 1,
                "unit_price": Decimal("500.00"),
                "nights": 2,
                "total_price": Decimal("1000.00"),
            }
        ],
    )
    assert booking.id is not None
    assert booking.org_id == DEFAULT_ORG_ID
    assert booking.status == BookingStatus.pending_payment.value
    assert booking.line_item_records is not None
    assert len(booking.line_item_records) == 1
    assert booking.line_item_records[0].total_price == Decimal("1000.00")

    # Get
    fetched = await repo.get(booking.id)
    assert fetched is not None
    assert fetched.id == booking.id

    # Update
    updated = await repo.update(fetched, {"status": BookingStatus.confirmed.value})
    assert updated.status == BookingStatus.confirmed.value

    # List
    items = await repo.get_multi()
    assert any(i.id == booking.id for i in items)

    # get_by_guest
    by_guest = await repo.get_by_guest(guest.id)
    assert len(by_guest) == 1
    assert by_guest[0].id == booking.id

    # get_by_property
    by_prop = await repo.get_by_property(prop.id)
    assert len(by_prop) == 1
    assert by_prop[0].id == booking.id

    # get_by_date_range
    by_range = await repo.get_by_date_range(date.today(), date.today())
    assert len(by_range) >= 1
    assert any(b.id == booking.id for b in by_range)

    # get_by_idempotency_key
    by_key = await repo.get_by_idempotency_key("key-123")
    assert by_key is None

    # Cancel (soft)
    cancelled = await repo.update(
        updated, {"status": BookingStatus.cancelled.value}
    )
    assert cancelled.status == BookingStatus.cancelled.value


@pytest.mark.asyncio
async def test_booking_api_crud(client: AsyncClient):
    # Create property and guest via API
    prop_resp = await client.post("/api/v1/properties/", json={"name": "Booking Test Hotel"})
    assert prop_resp.status_code == 201
    prop_id = prop_resp.json()["id"]

    guest_resp = await client.post(
        "/api/v1/users/",
        json={
            "email": f"api_guest_{uuid.uuid4().hex}@example.com",
            "password": "secret123",
            "first_name": "Api",
            "last_name": "Guest",
        },
    )
    assert guest_resp.status_code == 201
    guest_id = guest_resp.json()["id"]

    # Create booking
    response = await client.post(
        "/api/v1/bookings/",
        json={
            "booking_type": "room",
            "property_id": prop_id,
            "guest_id": guest_id,
            "check_in": str(date.today()),
            "check_out": str(date.today() + timedelta(days=2)),
            "status": "pending_payment",
            "gross_amount": "1500.00",
            "discount_amount": "0.00",
            "tax_amount": "180.00",
            "total_amount": "1680.00",
            "currency": "INR",
            "line_items": [
                {"item_type": "room", "item_id": str(uuid.uuid4()), "quantity": 1, "unit_price": "750.00", "nights": 2, "total_price": "1500.00"}
            ],
            "line_items_data": [
                {"item_type": "room", "item_id": str(uuid.uuid4()), "quantity": 1, "unit_price": "750.00", "nights": 2, "total_price": "1500.00"}
            ],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["booking_type"] == "room"
    assert data["property_id"] == prop_id
    assert data["guest_id"] == guest_id
    assert data["status"] == "pending_payment"
    assert Decimal(data["total_amount"]) == Decimal("1680.00")
    assert data["currency"] == "INR"
    assert len(data["line_item_records"]) == 1
    booking_id = data["id"]

    # List
    response = await client.get("/api/v1/bookings/")
    assert response.status_code == 200
    items = response.json()
    assert any(i["id"] == booking_id for i in items)

    # Get
    response = await client.get(f"/api/v1/bookings/{booking_id}")
    assert response.status_code == 200
    assert response.json()["id"] == booking_id

    # Update
    response = await client.patch(
        f"/api/v1/bookings/{booking_id}",
        json={"status": "confirmed"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"

    # Delete (soft cancel)
    response = await client.delete(f"/api/v1/bookings/{booking_id}")
    assert response.status_code == 204

    # Verify cancelled
    response = await client.get(f"/api/v1/bookings/{booking_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert response.json()["cancelled_at"] is not None


@pytest.mark.asyncio
async def test_booking_status_transitions(client: AsyncClient):
    prop_resp = await client.post("/api/v1/properties/", json={"name": "Status Hotel"})
    prop_id = prop_resp.json()["id"]

    guest_resp = await client.post(
        "/api/v1/users/",
        json={
            "email": f"status_guest_{uuid.uuid4().hex}@example.com",
            "password": "secret123",
        },
    )
    guest_id = guest_resp.json()["id"]

    # Create pending_payment booking
    resp = await client.post(
        "/api/v1/bookings/",
        json={
            "booking_type": "room",
            "property_id": prop_id,
            "guest_id": guest_id,
            "check_in": str(date.today()),
            "check_out": str(date.today() + timedelta(days=1)),
            "status": "pending_payment",
            "gross_amount": "100.00",
            "total_amount": "100.00",
        },
    )
    booking_id = resp.json()["id"]

    # Valid: pending_payment -> confirmed
    resp = await client.patch(f"/api/v1/bookings/{booking_id}", json={"status": "confirmed"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"

    # Valid: confirmed -> completed
    resp = await client.patch(f"/api/v1/bookings/{booking_id}", json={"status": "completed"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"

    # Invalid: completed -> pending_payment
    resp = await client.patch(f"/api/v1/bookings/{booking_id}", json={"status": "pending_payment"})
    assert resp.status_code == 400
    assert "Invalid status transition" in resp.json()["detail"]

    # Create another booking for cancelled terminal test
    resp = await client.post(
        "/api/v1/bookings/",
        json={
            "booking_type": "room",
            "property_id": prop_id,
            "guest_id": guest_id,
            "check_in": str(date.today() + timedelta(days=1)),
            "check_out": str(date.today() + timedelta(days=2)),
            "status": "pending_payment",
            "gross_amount": "100.00",
            "total_amount": "100.00",
        },
    )
    booking_id2 = resp.json()["id"]

    # Cancel it
    resp = await client.patch(f"/api/v1/bookings/{booking_id2}", json={"status": "cancelled"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"

    # Invalid: cancelled -> confirmed
    resp = await client.patch(f"/api/v1/bookings/{booking_id2}", json={"status": "confirmed"})
    assert resp.status_code == 400
    assert "Invalid status transition" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_booking_idempotency_key_uniqueness(client: AsyncClient):
    prop_resp = await client.post("/api/v1/properties/", json={"name": "Idempotency Hotel"})
    prop_id = prop_resp.json()["id"]

    guest_resp = await client.post(
        "/api/v1/users/",
        json={
            "email": f"idemp_guest_{uuid.uuid4().hex}@example.com",
            "password": "secret123",
        },
    )
    guest_id = guest_resp.json()["id"]

    payload = {
        "booking_type": "room",
        "property_id": prop_id,
        "guest_id": guest_id,
        "check_in": str(date.today()),
        "check_out": str(date.today() + timedelta(days=1)),
        "status": "pending_payment",
        "gross_amount": "100.00",
        "total_amount": "100.00",
        "idempotency_key": "unique-key-123",
    }

    resp1 = await client.post("/api/v1/bookings/", json=payload)
    assert resp1.status_code == 201

    resp2 = await client.post("/api/v1/bookings/", json=payload)
    assert resp2.status_code == 409
    assert "idempotency key already exists" in resp2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_booking_date_range_queries(client: AsyncClient):
    prop_resp = await client.post("/api/v1/properties/", json={"name": "Range Hotel"})
    prop_id = prop_resp.json()["id"]

    guest_resp = await client.post(
        "/api/v1/users/",
        json={
            "email": f"range_guest_{uuid.uuid4().hex}@example.com",
            "password": "secret123",
        },
    )
    guest_id = guest_resp.json()["id"]

    today = date.today()

    # Booking 1: today
    resp1 = await client.post(
        "/api/v1/bookings/",
        json={
            "booking_type": "room",
            "property_id": prop_id,
            "guest_id": guest_id,
            "check_in": str(today),
            "check_out": str(today + timedelta(days=1)),
            "status": "pending_payment",
            "gross_amount": "100.00",
            "total_amount": "100.00",
        },
    )
    assert resp1.status_code == 201
    id1 = resp1.json()["id"]

    # Booking 2: today + 5 days
    resp2 = await client.post(
        "/api/v1/bookings/",
        json={
            "booking_type": "room",
            "property_id": prop_id,
            "guest_id": guest_id,
            "check_in": str(today + timedelta(days=5)),
            "check_out": str(today + timedelta(days=6)),
            "status": "pending_payment",
            "gross_amount": "100.00",
            "total_amount": "100.00",
        },
    )
    assert resp2.status_code == 201
    id2 = resp2.json()["id"]

    # Query range that includes both
    resp = await client.get(
        f"/api/v1/bookings/by-date-range?check_in_from={today}&check_in_to={today + timedelta(days=10)}"
    )
    assert resp.status_code == 200
    results = resp.json()
    ids = {b["id"] for b in results}
    assert id1 in ids
    assert id2 in ids

    # Query range that includes only the first
    resp = await client.get(
        f"/api/v1/bookings/by-date-range?check_in_from={today}&check_in_to={today + timedelta(days=1)}"
    )
    assert resp.status_code == 200
    results = resp.json()
    ids = {b["id"] for b in results}
    assert id1 in ids
    assert id2 not in ids

    # Query by guest
    resp = await client.get(f"/api/v1/bookings/by-guest/{guest_id}")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 2

    # Query by property
    resp = await client.get(f"/api/v1/bookings/by-property/{prop_id}")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 2


@pytest.mark.asyncio
async def test_booking_not_found(client: AsyncClient):
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/bookings/{fake_id}")
    assert resp.status_code == 404

    resp = await client.patch(f"/api/v1/bookings/{fake_id}", json={"status": "confirmed"})
    assert resp.status_code == 404

    resp = await client.delete(f"/api/v1/bookings/{fake_id}")
    assert resp.status_code == 404
