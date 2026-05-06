"""ARQ worker settings for background task processing."""
import logging

from arq.connections import RedisSettings
from arq.cron import cron

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.logging_config import setup_logging
from app.tasks.hold_cleaner import hold_cleaner
from app.tasks.gmail_poller import gmail_poller

setup_logging()
logger = logging.getLogger(__name__)

settings = get_settings()


async def startup(ctx: dict) -> None:
    logger.info("Worker starting up")
    ctx["settings"] = settings
    ctx["session_factory"] = AsyncSessionLocal


async def shutdown(ctx: dict) -> None:
    logger.info("Worker shutting down")


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    on_startup = startup
    on_shutdown = shutdown
    functions = [hold_cleaner, gmail_poller]
    cron_jobs = [
        cron(
            hold_cleaner,
            hour={i for i in range(24)},
            minute={i for i in range(0, 60, 1)},
            name="hold_cleaner_every_minute",
        ),
        cron(
            gmail_poller,
            hour={i for i in range(24)},
            minute={i for i in range(0, 60, 5)},
            name="gmail_poller_every_5_min",
        ),
    ]
    max_jobs = 10
    health_check_interval = 30
    health_check_key = "arq:health"


if __name__ == "__main__":
    logger.info("Brekora Worker module loaded")
