"""Tests for ARQ worker configuration and background tasks."""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import uuid

from app.models.inventory_hold import InventoryHold
from app.tasks.gmail_poller import gmail_poller
from app.tasks.hold_cleaner import hold_cleaner
from app.worker import WorkerSettings


class FakeSessionContext:
    """Async context manager that yields a mock session."""

    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *args):
        pass


def test_worker_settings():
    assert WorkerSettings.redis_settings is not None
    assert WorkerSettings.on_startup is not None
    assert WorkerSettings.on_shutdown is not None
    assert len(WorkerSettings.functions) == 2
    assert len(WorkerSettings.cron_jobs) == 2


@pytest.mark.asyncio
async def test_hold_cleaner_runs_against_real_db(db_session):
    """When the inventory_hold table exists, task executes cleanly (no rows to release)."""
    ctx = {"session_factory": lambda: FakeSessionContext(db_session)}
    result = await hold_cleaner(ctx)
    assert isinstance(result, dict)
    assert result["status"] == "ok"
    assert result["released"] >= 0
    assert "checked_at" in result


@pytest.mark.asyncio
async def test_hold_cleaner_skips_when_table_missing():
    """When the inventory_hold table does not exist yet, task skips gracefully."""
    from sqlalchemy.exc import ProgrammingError

    mock_session = AsyncMock()
    mock_session.execute.side_effect = ProgrammingError("statement", "params", "orig")

    ctx = {"session_factory": lambda: FakeSessionContext(mock_session)}
    result = await hold_cleaner(ctx)
    assert isinstance(result, dict)
    assert result["status"] == "skipped"
    assert "checked_at" in result


@pytest.mark.asyncio
async def test_hold_cleaner_releases_expired_holds():
    """hold_cleaner queries expired holds and calls release_inventory for each."""
    fake_hold = MagicMock(spec=InventoryHold)
    fake_hold.id = uuid.uuid4()
    fake_hold.booking_id = uuid.uuid4()

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [fake_hold]

    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result

    ctx = {"session_factory": lambda: FakeSessionContext(mock_session)}

    with patch("app.tasks.hold_cleaner.InventoryService") as MockService:
        mock_svc = AsyncMock()
        mock_svc.release_inventory.return_value = True
        MockService.return_value = mock_svc

        result = await hold_cleaner(ctx)

    assert result["status"] == "ok"
    assert result["released"] == 1
    mock_svc.release_inventory.assert_awaited_once_with(fake_hold.id)


@pytest.mark.asyncio
async def test_gmail_poller_runs():
    """gmail_poller returns expected payload when no credentials available."""
    ctx = {}
    with patch(
        "app.tasks.gmail_poller.GmailOAuthService.get_credentials",
        return_value=None,
    ):
        result = await gmail_poller(ctx)
    assert isinstance(result, dict)
    assert result["status"] == "ok"
    assert result["processed"] == 0
    assert "checked_at" in result
    assert "correlation_id" in result


@pytest.mark.asyncio
async def test_tasks_are_idempotent():
    """Running the same task twice with identical state must not error."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    ctx = {"session_factory": lambda: FakeSessionContext(mock_session)}

    with patch("app.tasks.hold_cleaner.InventoryService") as MockService:
        mock_svc = AsyncMock()
        MockService.return_value = mock_svc

        r1 = await hold_cleaner(ctx)
        r2 = await hold_cleaner(ctx)

    assert r1["status"] == "ok"
    assert r2["status"] == "ok"
    assert mock_session.execute.await_count == 2
