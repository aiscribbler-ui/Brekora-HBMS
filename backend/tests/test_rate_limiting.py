import pytest
from httpx import AsyncClient

from app.core.redis import get_redis_client
from app.main import app


@pytest.fixture
def fake_redis(client: AsyncClient):
    # The client fixture installs a fake redis override; retrieve it via the app state.
    # Because FakeRedis is created per client fixture and shared, tests should clean up keys.
    override = app.dependency_overrides.get(get_redis_client)
    if override:
        import asyncio
        return asyncio.get_event_loop().run_until_complete(override())
    pytest.skip("FakeRedis not available")


async def _clear_rate_limit_keys(fake_redis, category: str, identifier: str):
    key = f"ratelimit:{category}:{identifier}"
    await fake_redis.delete(key)


@pytest.mark.asyncio(loop_scope="session")
async def test_health_check_exempt_from_rate_limit(client: AsyncClient):
    for _ in range(10):
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


@pytest.mark.asyncio(loop_scope="session")
async def test_docs_exempt_from_rate_limit(client: AsyncClient):
    response = await client.get("/docs")
    assert response.status_code in (200, 307)


@pytest.mark.asyncio(loop_scope="session")
async def test_openapi_json_exempt_from_rate_limit(client: AsyncClient):
    response = await client.get("/openapi.json")
    assert response.status_code in (200, 307)


@pytest.mark.asyncio(loop_scope="session")
async def test_login_rate_limit_by_ip(client: AsyncClient):
    # Temporarily override limits for this test
    original_config = getattr(app.state, "rate_limit_config", None)
    app.state.rate_limit_config = {
        "login": {"max_requests": 3, "window_seconds": 60, "identifier_type": "ip"}
    }

    fake_redis_instance = await app.dependency_overrides[get_redis_client]()
    await _clear_rate_limit_keys(fake_redis_instance, "login", "unknown")
    await _clear_rate_limit_keys(fake_redis_instance, "login", "testserver")
    await _clear_rate_limit_keys(fake_redis_instance, "login", "127.0.0.1")

    try:
        # 3 requests should be allowed (endpoint returns 401 for bad creds)
        for _ in range(3):
            response = await client.post("/api/v1/auth/login", json={"email": "a@b.com", "password": "wrong"})
            assert response.status_code == 401

        # 4th request should be rate limited by middleware
        response = await client.post("/api/v1/auth/login", json={"email": "a@b.com", "password": "wrong"})
        assert response.status_code == 429
        assert "Retry-After" in response.headers
        retry_after = int(response.headers["Retry-After"])
        assert 1 <= retry_after <= 60
        assert "Rate limit exceeded" in response.json()["detail"]
    finally:
        if original_config is not None:
            app.state.rate_limit_config = original_config
        else:
            delattr(app.state, "rate_limit_config")
        await _clear_rate_limit_keys(fake_redis_instance, "login", "unknown")
        await _clear_rate_limit_keys(fake_redis_instance, "login", "testserver")
        await _clear_rate_limit_keys(fake_redis_instance, "login", "127.0.0.1")


@pytest.mark.asyncio(loop_scope="session")
async def test_search_rate_limit_by_ip(client: AsyncClient):
    original_config = getattr(app.state, "rate_limit_config", None)
    app.state.rate_limit_config = {
        "search": {"max_requests": 3, "window_seconds": 60, "identifier_type": "ip"}
    }

    fake_redis_instance = await app.dependency_overrides[get_redis_client]()
    await _clear_rate_limit_keys(fake_redis_instance, "search", "unknown")
    await _clear_rate_limit_keys(fake_redis_instance, "search", "testserver")
    await _clear_rate_limit_keys(fake_redis_instance, "search", "127.0.0.1")

    try:
        for _ in range(3):
            response = await client.get("/api/v1/search")
            # Endpoint doesn't exist yet; middleware should allow, then 404
            assert response.status_code == 404

        response = await client.get("/api/v1/search")
        assert response.status_code == 429
        assert "Retry-After" in response.headers
        assert "Rate limit exceeded" in response.json()["detail"]
    finally:
        if original_config is not None:
            app.state.rate_limit_config = original_config
        else:
            delattr(app.state, "rate_limit_config")
        await _clear_rate_limit_keys(fake_redis_instance, "search", "unknown")
        await _clear_rate_limit_keys(fake_redis_instance, "search", "testserver")
        await _clear_rate_limit_keys(fake_redis_instance, "search", "127.0.0.1")


@pytest.mark.asyncio(loop_scope="session")
async def test_hold_rate_limit_by_session(client: AsyncClient):
    original_config = getattr(app.state, "rate_limit_config", None)
    app.state.rate_limit_config = {
        "hold": {"max_requests": 2, "window_seconds": 60, "identifier_type": "session"}
    }

    fake_redis_instance = await app.dependency_overrides[get_redis_client]()

    try:
        # No session header -> falls back to IP
        for _ in range(2):
            response = await client.post("/api/v1/bookings/init")
            assert response.status_code == 404

        response = await client.post("/api/v1/bookings/init")
        assert response.status_code == 429
        assert "Retry-After" in response.headers

        # With a session header, separate counter
        await _clear_rate_limit_keys(fake_redis_instance, "hold", "sess_123")
        for _ in range(2):
            response = await client.post(
                "/api/v1/bookings/init", headers={"X-Session-ID": "sess_123"}
            )
            assert response.status_code == 404

        response = await client.post(
            "/api/v1/bookings/init", headers={"X-Session-ID": "sess_123"}
        )
        assert response.status_code == 429
    finally:
        if original_config is not None:
            app.state.rate_limit_config = original_config
        else:
            delattr(app.state, "rate_limit_config")
        await _clear_rate_limit_keys(fake_redis_instance, "hold", "unknown")
        await _clear_rate_limit_keys(fake_redis_instance, "hold", "testserver")
        await _clear_rate_limit_keys(fake_redis_instance, "hold", "127.0.0.1")
        await _clear_rate_limit_keys(fake_redis_instance, "hold", "sess_123")


@pytest.mark.asyncio(loop_scope="session")
async def test_promo_rate_limit_by_ip(client: AsyncClient):
    original_config = getattr(app.state, "rate_limit_config", None)
    app.state.rate_limit_config = {
        "promo": {"max_requests": 2, "window_seconds": 60, "identifier_type": "ip"}
    }

    fake_redis_instance = await app.dependency_overrides[get_redis_client]()
    await _clear_rate_limit_keys(fake_redis_instance, "promo", "unknown")
    await _clear_rate_limit_keys(fake_redis_instance, "promo", "testserver")
    await _clear_rate_limit_keys(fake_redis_instance, "promo", "127.0.0.1")

    try:
        for _ in range(2):
            response = await client.post("/api/v1/promo-codes/validate")
            assert response.status_code == 404

        response = await client.post("/api/v1/promo-codes/validate")
        assert response.status_code == 429
        assert "Retry-After" in response.headers
    finally:
        if original_config is not None:
            app.state.rate_limit_config = original_config
        else:
            delattr(app.state, "rate_limit_config")
        await _clear_rate_limit_keys(fake_redis_instance, "promo", "unknown")
        await _clear_rate_limit_keys(fake_redis_instance, "promo", "testserver")
        await _clear_rate_limit_keys(fake_redis_instance, "promo", "127.0.0.1")


@pytest.mark.asyncio(loop_scope="session")
async def test_booking_rate_limit_by_session(client: AsyncClient):
    original_config = getattr(app.state, "rate_limit_config", None)
    app.state.rate_limit_config = {
        "booking": {"max_requests": 2, "window_seconds": 60, "identifier_type": "session"}
    }

    fake_redis_instance = await app.dependency_overrides[get_redis_client]()

    try:
        for _ in range(2):
            response = await client.post("/api/v1/bookings")
            assert response.status_code == 404

        response = await client.post("/api/v1/bookings")
        assert response.status_code == 429
        assert "Retry-After" in response.headers

        # Different session should have its own counter
        await _clear_rate_limit_keys(fake_redis_instance, "booking", "sess_booking")
        for _ in range(2):
            response = await client.post(
                "/api/v1/bookings", headers={"X-Session-ID": "sess_booking"}
            )
            assert response.status_code == 404

        response = await client.post(
            "/api/v1/bookings", headers={"X-Session-ID": "sess_booking"}
        )
        assert response.status_code == 429
    finally:
        if original_config is not None:
            app.state.rate_limit_config = original_config
        else:
            delattr(app.state, "rate_limit_config")
        await _clear_rate_limit_keys(fake_redis_instance, "booking", "unknown")
        await _clear_rate_limit_keys(fake_redis_instance, "booking", "testserver")
        await _clear_rate_limit_keys(fake_redis_instance, "booking", "127.0.0.1")
        await _clear_rate_limit_keys(fake_redis_instance, "booking", "sess_booking")


@pytest.mark.asyncio(loop_scope="session")
async def test_rate_limit_key_format(client: AsyncClient):
    original_config = getattr(app.state, "rate_limit_config", None)
    app.state.rate_limit_config = {
        "login": {"max_requests": 1, "window_seconds": 60, "identifier_type": "ip"}
    }

    fake_redis_instance = await app.dependency_overrides[get_redis_client]()
    await _clear_rate_limit_keys(fake_redis_instance, "login", "unknown")
    await _clear_rate_limit_keys(fake_redis_instance, "login", "testserver")
    await _clear_rate_limit_keys(fake_redis_instance, "login", "127.0.0.1")

    try:
        response = await client.post("/api/v1/auth/login", json={"email": "a@b.com", "password": "wrong"})
        assert response.status_code == 401

        # Verify the key exists in Redis with correct format
        key = "ratelimit:login:testserver"
        val = await fake_redis_instance.zcard(key)
        if val == 0:
            key = "ratelimit:login:unknown"
            val = await fake_redis_instance.zcard(key)
        assert val == 1
    finally:
        if original_config is not None:
            app.state.rate_limit_config = original_config
        else:
            delattr(app.state, "rate_limit_config")
        await _clear_rate_limit_keys(fake_redis_instance, "login", "unknown")
        await _clear_rate_limit_keys(fake_redis_instance, "login", "testserver")
        await _clear_rate_limit_keys(fake_redis_instance, "login", "127.0.0.1")
