import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cancellation_policy import CancellationPolicy
from app.repositories.cancellation_policy import CancellationPolicyRepository
from app.services.refund_calculator import RefundCalculator

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.mark.asyncio
async def test_cancellation_policy_repository_crud(db_session: AsyncSession):
    repo = CancellationPolicyRepository(db_session, DEFAULT_ORG_ID)

    # Create
    policy = await repo.create(
        {
            "name": "Flexible",
            "free_cancellation_hours": 48,
            "partial_refund_hours": 24,
            "partial_refund_percentage": Decimal("50.00"),
            "non_refundable_hours": 24,
            "is_non_refundable": False,
        }
    )
    assert policy.id is not None
    assert policy.name == "Flexible"
    assert policy.org_id == DEFAULT_ORG_ID

    # Get
    fetched = await repo.get(policy.id)
    assert fetched is not None
    assert fetched.name == "Flexible"

    # Update
    updated = await repo.update(fetched, {"name": "Super Flexible"})
    assert updated.name == "Super Flexible"

    # List
    items = await repo.get_multi()
    assert any(i.id == policy.id for i in items)

    # Delete
    await repo.delete(updated)
    after_delete = await repo.get(policy.id)
    assert after_delete is None


@pytest.mark.asyncio
async def test_cancellation_policy_api_crud(client: AsyncClient):
    # Create
    response = await client.post(
        "/api/v1/cancellation-policies/",
        json={
            "name": "Strict",
            "free_cancellation_hours": 72,
            "partial_refund_hours": 48,
            "partial_refund_percentage": "75.00",
            "non_refundable_hours": 48,
            "is_non_refundable": False,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Strict"
    assert data["free_cancellation_hours"] == 72
    assert data["partial_refund_hours"] == 48
    assert data["partial_refund_percentage"] == "75.00"
    assert data["is_non_refundable"] is False
    assert data["org_id"] == str(DEFAULT_ORG_ID)
    policy_id = data["id"]

    # List
    response = await client.get("/api/v1/cancellation-policies/")
    assert response.status_code == 200
    items = response.json()
    assert any(i["id"] == policy_id for i in items)

    # Get
    response = await client.get(f"/api/v1/cancellation-policies/{policy_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Strict"

    # Update
    response = await client.patch(
        f"/api/v1/cancellation-policies/{policy_id}",
        json={"name": "Moderate", "free_cancellation_hours": 48},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Moderate"
    assert response.json()["free_cancellation_hours"] == 48

    # Delete
    response = await client.delete(f"/api/v1/cancellation-policies/{policy_id}")
    assert response.status_code == 204

    # Verify deletion
    response = await client.get(f"/api/v1/cancellation-policies/{policy_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cancellation_policy_not_found(client: AsyncClient):
    fake_id = str(uuid.uuid4())

    response = await client.get(f"/api/v1/cancellation-policies/{fake_id}")
    assert response.status_code == 404

    response = await client.patch(
        f"/api/v1/cancellation-policies/{fake_id}", json={"name": "X"}
    )
    assert response.status_code == 404

    response = await client.delete(f"/api/v1/cancellation-policies/{fake_id}")
    assert response.status_code == 404


def test_refund_calculator_free_cancellation():
    policy = CancellationPolicy(
        name="Flexible",
        free_cancellation_hours=48,
        partial_refund_hours=24,
        partial_refund_percentage=Decimal("50.00"),
        non_refundable_hours=24,
        is_non_refundable=False,
    )
    amount = Decimal("1000.00")

    # Well within free window
    refund = RefundCalculator.calculate_refund(amount, policy, 72)
    assert refund == Decimal("1000.00")

    # Exactly at free window boundary
    refund = RefundCalculator.calculate_refund(amount, policy, 48)
    assert refund == Decimal("1000.00")


def test_refund_calculator_partial_refund():
    policy = CancellationPolicy(
        name="Flexible",
        free_cancellation_hours=48,
        partial_refund_hours=24,
        partial_refund_percentage=Decimal("50.00"),
        non_refundable_hours=24,
        is_non_refundable=False,
    )
    amount = Decimal("1000.00")

    # Within partial window
    refund = RefundCalculator.calculate_refund(amount, policy, 36)
    assert refund == Decimal("500.00")

    # Exactly at partial window boundary
    refund = RefundCalculator.calculate_refund(amount, policy, 24)
    assert refund == Decimal("500.00")


def test_refund_calculator_non_refundable_window():
    policy = CancellationPolicy(
        name="Flexible",
        free_cancellation_hours=48,
        partial_refund_hours=24,
        partial_refund_percentage=Decimal("50.00"),
        non_refundable_hours=24,
        is_non_refundable=False,
    )
    amount = Decimal("1000.00")

    # Below partial window -> 0 refund
    refund = RefundCalculator.calculate_refund(amount, policy, 12)
    assert refund == Decimal("0.00")

    # Zero hours -> 0 refund
    refund = RefundCalculator.calculate_refund(amount, policy, 0)
    assert refund == Decimal("0.00")


def test_refund_calculator_non_refundable_policy():
    policy = CancellationPolicy(
        name="Non-Refundable",
        free_cancellation_hours=None,
        partial_refund_hours=None,
        partial_refund_percentage=None,
        non_refundable_hours=None,
        is_non_refundable=True,
    )
    amount = Decimal("1000.00")

    # Any cancellation time returns 0
    refund = RefundCalculator.calculate_refund(amount, policy, 999)
    assert refund == Decimal("0.00")

    refund = RefundCalculator.calculate_refund(amount, policy, 0)
    assert refund == Decimal("0.00")


def test_refund_calculator_no_partial_refund_configured():
    policy = CancellationPolicy(
        name="Free Only",
        free_cancellation_hours=48,
        partial_refund_hours=None,
        partial_refund_percentage=None,
        non_refundable_hours=None,
        is_non_refundable=False,
    )
    amount = Decimal("1000.00")

    refund = RefundCalculator.calculate_refund(amount, policy, 72)
    assert refund == Decimal("1000.00")

    refund = RefundCalculator.calculate_refund(amount, policy, 36)
    assert refund == Decimal("0.00")


def test_refund_calculator_gst_and_ota_not_refundable():
    """GST and OTA commissions should be deducted from the amount
    passed to the calculator; the calculator itself operates on the
    net refundable amount.
    """
    policy = CancellationPolicy(
        name="Flexible",
        free_cancellation_hours=48,
        partial_refund_hours=24,
        partial_refund_percentage=Decimal("50.00"),
        non_refundable_hours=24,
        is_non_refundable=False,
    )
    gross_amount = Decimal("1180.00")  # includes 180 GST
    gst = Decimal("180.00")
    ota_commission = Decimal("100.00")
    net_refundable = gross_amount - gst - ota_commission  # 900.00

    refund = RefundCalculator.calculate_refund(net_refundable, policy, 36)
    assert refund == Decimal("450.00")
