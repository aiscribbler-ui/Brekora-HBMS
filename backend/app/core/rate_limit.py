import time
import uuid
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.redis import get_redis_client


# Default rate limit rules (override via app.state.rate_limit_config)
DEFAULT_RATE_LIMIT_CONFIG = {
    "search": {"max_requests": 30, "window_seconds": 60, "identifier_type": "ip"},
    "hold": {"max_requests": 5, "window_seconds": 600, "identifier_type": "session"},
    "promo": {"max_requests": 10, "window_seconds": 60, "identifier_type": "ip"},
    "booking": {"max_requests": 3, "window_seconds": 300, "identifier_type": "session"},
    "login": {"max_requests": 5, "window_seconds": 900, "identifier_type": "ip"},
}

# Paths exempt from rate limiting
EXEMPT_PATHS = {
    "/api/v1/health",
    "/docs",
    "/openapi.json",
    "/redoc",
}

# (method, exact_path, category)
CATEGORY_RULES = [
    ("POST", "/api/v1/auth/login", "login"),
    ("POST", "/api/v1/auth/login/", "login"),
    ("GET", "/api/v1/search", "search"),
    ("POST", "/api/v1/search", "search"),
    ("POST", "/api/v1/search/", "search"),
    ("POST", "/api/v1/bookings/init", "hold"),
    ("POST", "/api/v1/bookings/init/", "hold"),
    ("POST", "/api/v1/promo-codes/validate", "promo"),
    ("POST", "/api/v1/promo-codes/validate/", "promo"),
    ("POST", "/api/v1/bookings", "booking"),
    ("POST", "/api/v1/bookings/", "booking"),
]


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _get_session_id(request: Request) -> str:
    session_id = request.headers.get("x-session-id")
    if session_id:
        return session_id
    session_cookie = request.cookies.get("session")
    if session_cookie:
        return session_cookie
    return _get_client_ip(request)


def _get_identifier(request: Request, identifier_type: str) -> str:
    if identifier_type == "session":
        return _get_session_id(request)
    return _get_client_ip(request)


def _match_category(method: str, path: str) -> str | None:
    for rule_method, rule_path, category in CATEGORY_RULES:
        if rule_method != "*" and rule_method != method.upper():
            continue
        if path == rule_path:
            return category
    return None


async def _check_sliding_window(
    redis_client,
    category: str,
    identifier: str,
    max_requests: int,
    window_seconds: int,
) -> tuple[bool, int]:
    key = f"ratelimit:{category}:{identifier}"
    now = time.time()
    window_start = now - window_seconds

    await redis_client.zremrangebyscore(key, 0, window_start)
    current_count = await redis_client.zcard(key)

    if current_count >= max_requests:
        oldest = await redis_client.zrange(key, 0, 0, withscores=True)
        if oldest:
            retry_after = max(1, int(window_seconds - (now - oldest[0][1])))
        else:
            retry_after = window_seconds
        return False, retry_after

    member = f"{now}:{uuid.uuid4().hex}"
    await redis_client.zadd(key, {member: now})
    await redis_client.expire(key, window_seconds)
    return True, 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        if path in EXEMPT_PATHS:
            return await call_next(request)
        if path.startswith("/docs/") or path.startswith("/redoc/"):
            return await call_next(request)

        category = _match_category(request.method, path)
        if not category:
            return await call_next(request)

        # Allow tests to override limits via app.state
        app_config = getattr(request.app.state, "rate_limit_config", None)
        if app_config and category in app_config:
            config = app_config[category]
        else:
            config = DEFAULT_RATE_LIMIT_CONFIG[category]

        identifier = _get_identifier(request, config["identifier_type"])

        # Support test dependency overrides for redis
        redis_factory = request.app.dependency_overrides.get(get_redis_client)
        if redis_factory:
            redis_client = await redis_factory()
        else:
            redis_client = await get_redis_client()

        allowed, retry_after = await _check_sliding_window(
            redis_client,
            category,
            identifier,
            config["max_requests"],
            config["window_seconds"],
        )

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please try again later."},
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)
