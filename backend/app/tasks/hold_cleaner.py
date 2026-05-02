"""Release expired inventory holds."""
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import ProgrammingError

from app.db.session import AsyncSessionLocal
from app.models.inventory_hold import InventoryHold
from app.services.inventory_service import InventoryService

logger = logging.getLogger(__name__)


async def hold_cleaner(ctx: dict) -> dict:
    """Release expired inventory holds. Runs every minute. Idempotent."""
    logger.info("hold_cleaner started")
    session_factory = ctx.get("session_factory", AsyncSessionLocal)
    result = {
        "released": 0,
        "status": "ok",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        async with session_factory() as session:
            stmt = select(InventoryHold).where(
                InventoryHold.status == "active",
                InventoryHold.expires_at < datetime.now(timezone.utc),
            )
            res = await session.execute(stmt)
            expired_holds = res.scalars().all()

            service = InventoryService(session)
            for hold in expired_holds:
                try:
                    ok = await service.release_inventory(hold.id)
                    if ok:
                        result["released"] += 1
                        logger.info(
                            "hold_cleaner released hold %s for booking %s",
                            hold.id,
                            hold.booking_id,
                        )
                except Exception:
                    logger.exception(
                        "hold_cleaner failed to release hold %s", hold.id
                    )
    except ProgrammingError as exc:
        logger.warning(
            "hold_cleaner: inventory_hold table not ready yet (%s)", exc
        )
        result["status"] = "skipped"
    except Exception:
        logger.exception("hold_cleaner failed")
        result["status"] = "error"
        raise

    logger.info("hold_cleaner finished, released %s holds", result["released"])
    return result
