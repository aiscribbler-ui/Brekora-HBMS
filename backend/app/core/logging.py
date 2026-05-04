"""Structured logging configuration using structlog."""
import logging
import sys
from typing import Any

import structlog
from structlog.stdlib import LoggerFactory


def configure_logging(*, json_logs: bool = False, log_level: str = "INFO") -> None:
    """Configure structlog and stdlib logging.

    Args:
        json_logs: When True, output JSON; otherwise colored console.
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    structlog.reset_defaults()

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.stdlib.ExtraAdder(),
        structlog.processors.CallsiteParameterAdder(
            {
                structlog.processors.CallsiteParameter.PATHNAME,
                structlog.processors.CallsiteParameter.LINENO,
            }
        ),
    ]

    if json_logs:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging to route through structlog
    stdlib_handler: logging.Handler = logging.StreamHandler(sys.stdout)
    stdlib_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=renderer,
            foreign_pre_chain=shared_processors,
        )
    )

    root_logger = logging.getLogger()
    root_logger.handlers = [stdlib_handler]
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Uvicorn loggers
    for uvicorn_logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        uvicorn_logger = logging.getLogger(uvicorn_logger_name)
        uvicorn_logger.handlers = [stdlib_handler]
        uvicorn_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        uvicorn_logger.propagate = False


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger instance."""
    return structlog.get_logger(name)


# ---------------------------------------------------------------------------
# Business-event helpers
# ---------------------------------------------------------------------------

def log_booking_created(
    *,
    booking_id: str,
    user_id: str | None = None,
    org_id: str | None = None,
    property_id: str | None = None,
    total_amount: float | None = None,
    source: str | None = None,
    **extra: Any,
) -> None:
    """Emit a structured 'booking_created' business event."""
    logger = get_logger("brekora.events")
    logger.info(
        "booking_created",
        event_type="booking_created",
        booking_id=booking_id,
        user_id=user_id,
        org_id=org_id,
        property_id=property_id,
        total_amount=total_amount,
        source=source,
        **extra,
    )


def log_payment_failed(
    *,
    booking_id: str,
    user_id: str | None = None,
    org_id: str | None = None,
    amount: float | None = None,
    reason: str | None = None,
    payment_provider: str | None = None,
    **extra: Any,
) -> None:
    """Emit a structured 'payment_failed' business event."""
    logger = get_logger("brekora.events")
    logger.warning(
        "payment_failed",
        event_type="payment_failed",
        booking_id=booking_id,
        user_id=user_id,
        org_id=org_id,
        amount=amount,
        reason=reason,
        payment_provider=payment_provider,
        **extra,
    )


def log_booking_cancelled(
    *,
    booking_id: str,
    user_id: str | None = None,
    org_id: str | None = None,
    cancellation_reason: str | None = None,
    refund_amount: float | None = None,
    **extra: Any,
) -> None:
    """Emit a structured 'booking_cancelled' business event."""
    logger = get_logger("brekora.events")
    logger.info(
        "booking_cancelled",
        event_type="booking_cancelled",
        booking_id=booking_id,
        user_id=user_id,
        org_id=org_id,
        cancellation_reason=cancellation_reason,
        refund_amount=refund_amount,
        **extra,
    )
