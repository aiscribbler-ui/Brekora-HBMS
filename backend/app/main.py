from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.rate_limit import RateLimitMiddleware
from app.middleware.correlation_id import CorrelationIdMiddleware

settings = get_settings()

configure_logging(
    json_logs=settings.ENVIRONMENT == "production",
    log_level=settings.LOG_LEVEL,
)

# Conditional Sentry initialisation
if settings.SENTRY_DSN:
    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=1.0 if settings.ENVIRONMENT == "production" else 0.0,
    )

app = FastAPI(
    title="Brekora BMS API",
    description="Booking Manager System backend API",
    version="0.1.0",
)

app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(RateLimitMiddleware)

app.include_router(api_router, prefix="/api/v1")


@app.get("/api/v1/health", tags=["health"])
async def health_check() -> JSONResponse:
    return JSONResponse(content={"status": "ok"}, status_code=200)
