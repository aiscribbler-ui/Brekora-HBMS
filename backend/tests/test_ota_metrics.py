"""Tests for parser accuracy telemetry (ParseMetric)."""
from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import DEFAULT_BREKORA_ORG_ID
from app.core.security import create_access_token, get_password_hash
from app.models.parse_metric import ParseMetric
from app.models.role import Role
from app.models.user import User
from app.repositories.user import UserRepository
from app.services.parse_metric_service import ParseMetricService


async def _create_admin_user(db_session: AsyncSession) -> User:
    result = await db_session.execute(
        select(Role).where(Role.name == "Admin", Role.org_id == DEFAULT_BREKORA_ORG_ID)
    )
    role = result.scalar_one_or_none()
    repo = UserRepository(db_session, DEFAULT_BREKORA_ORG_ID)
    return await repo.create(
        {
            "email": "admin_metrics@example.com",
            "password_hash": get_password_hash("password"),
            "first_name": "Admin",
            "last_name": "Metrics",
            "role_id": role.id if role else None,
        }
    )


@pytest.mark.asyncio
async def test_record_parse_increments_counters(db_session: AsyncSession):
    svc = ParseMetricService(db_session)
    metric = await svc.record_parse("test_airbnb", success=True, confidence=0.85)
    assert metric.ota_source == "test_airbnb"
    assert metric.total_parsed == 1
    assert metric.successful == 1
    assert metric.failed == 0
    assert float(metric.avg_confidence) == pytest.approx(0.85)

    metric2 = await svc.record_parse("test_airbnb", success=False, confidence=0.0)
    assert metric2.total_parsed == 2
    assert metric2.successful == 1
    assert metric2.failed == 1
    # avg_confidence = (0.85 * 1 + 0.0) / 2 = 0.425
    assert float(metric2.avg_confidence) == pytest.approx(0.425)


@pytest.mark.asyncio
async def test_accuracy_calculation(db_session: AsyncSession):
    svc = ParseMetricService(db_session)
    today = date.today()

    for i in range(5):
        d = today - timedelta(days=i)
        m = ParseMetric(
            ota_source="test_mmt",
            date=d,
            total_parsed=10,
            successful=7,
            failed=3,
            avg_confidence=0.7,
        )
        db_session.add(m)
    await db_session.flush()

    accuracy = await svc.get_accuracy("test_mmt", days=3)
    # last 3 days including today: 3 days * 10 parsed = 30 total, 21 successful
    assert accuracy == 0.7

    accuracy_all = await svc.get_accuracy("test_mmt", days=10)
    assert accuracy_all == 0.7


@pytest.mark.asyncio
async def test_accuracy_zero_total(db_session: AsyncSession):
    svc = ParseMetricService(db_session)
    accuracy = await svc.get_accuracy("unknown", days=30)
    assert accuracy == 0.0


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_metrics(client: AsyncClient, db_session: AsyncSession):
    svc = ParseMetricService(db_session)
    await svc.record_parse("test_goibibo", success=True, confidence=0.9)
    await svc.record_parse("test_goibibo", success=False, confidence=0.0)

    admin = await _create_admin_user(db_session)
    token = create_access_token(admin.id, admin.org_id)

    today = date.today()
    start = today - timedelta(days=1)
    end = today + timedelta(days=1)

    response = await client.get(
        "/api/v1/ota/metrics/",
        params={"start": start.isoformat(), "end": end.isoformat()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    goibibo_metrics = [m for m in data if m["ota_source"] == "test_goibibo"]
    assert len(goibibo_metrics) >= 1
    assert goibibo_metrics[0]["total_parsed"] == 2
    assert goibibo_metrics[0]["successful"] == 1
    assert goibibo_metrics[0]["failed"] == 1


@pytest.mark.asyncio
async def test_metrics_endpoint_admin_only(client: AsyncClient, db_session: AsyncSession):
    # Create a non-admin user
    repo = UserRepository(db_session, DEFAULT_BREKORA_ORG_ID)
    guest = await repo.create(
        {
            "email": "guest_metrics@example.com",
            "password_hash": get_password_hash("password"),
            "first_name": "Guest",
            "last_name": "Metrics",
        }
    )
    token = create_access_token(guest.id, guest.org_id)

    today = date.today()
    response = await client.get(
        "/api/v1/ota/metrics/",
        params={"start": today.isoformat(), "end": today.isoformat()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "User has no assigned role"


@pytest.mark.asyncio
async def test_accuracy_endpoint(client: AsyncClient, db_session: AsyncSession):
    svc = ParseMetricService(db_session)
    today = date.today()
    db_session.add(
        ParseMetric(
            ota_source="test_airbnb",
            date=today,
            total_parsed=10,
            successful=8,
            failed=2,
            avg_confidence=0.8,
        )
    )
    await db_session.flush()

    admin = await _create_admin_user(db_session)
    token = create_access_token(admin.id, admin.org_id)

    response = await client.get(
        "/api/v1/ota/metrics/accuracy",
        params={"ota_source": "test_airbnb", "days": 7},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ota_source"] == "test_airbnb"
    assert data["days"] == 7
    assert data["accuracy"] == 0.8
