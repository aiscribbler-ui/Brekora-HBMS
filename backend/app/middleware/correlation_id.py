"""Correlation-ID middleware for request tracing."""
import contextvars
import uuid
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

CORRELATION_ID_CTX_VAR: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "correlation_id", default=None
)

CORRELATION_ID_HEADER = "X-Correlation-ID"


def get_correlation_id() -> Optional[str]:
    """Return the current request's correlation ID, if any."""
    return CORRELATION_ID_CTX_VAR.get()


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Generate or propagate a correlation ID across the request/response lifecycle."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Use existing header or generate a new UUID
        header_value = request.headers.get(CORRELATION_ID_HEADER)
        correlation_id = header_value if header_value else str(uuid.uuid4())

        token = CORRELATION_ID_CTX_VAR.set(correlation_id)
        try:
            response = await call_next(request)
            response.headers[CORRELATION_ID_HEADER] = correlation_id
            return response
        finally:
            CORRELATION_ID_CTX_VAR.reset(token)
