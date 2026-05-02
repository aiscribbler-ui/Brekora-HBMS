from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from testcontainers.postgres import PostgresContainer

from app.core.redis import get_redis_client
from app.db.session import get_db
from app.models import Base
from app.main import app


class FakeRedisPipeline:
    def __init__(self, redis):
        self.redis = redis
        self.commands = []

    def incr(self, key):
        self.commands.append(("incr", key))
        return self

    def expire(self, key, seconds):
        self.commands.append(("expire", key, seconds))
        return self

    async def execute(self):
        results = []
        for cmd, *args in self.commands:
            if cmd == "incr":
                results.append(self.redis.incr(args[0]))
            elif cmd == "expire":
                results.append(await self.redis.expire(args[0], args[1]))
        self.commands = []
        return results


class FakeRedis:
    def __init__(self):
        self._data = {}
        self._zsets = {}
        self._zset_expiry = {}
        self._hashes = {}
        self._hash_expiry = {}

    def _check_zset_expired(self, key):
        import time

        if key in self._zset_expiry and time.time() > self._zset_expiry[key]:
            self._zsets.pop(key, None)
            self._zset_expiry.pop(key, None)
            return True
        return False

    def _check_hash_expired(self, key):
        import time

        if key in self._hash_expiry and time.time() > self._hash_expiry[key]:
            self._hashes.pop(key, None)
            self._hash_expiry.pop(key, None)
            return True
        return False

    async def get(self, key):
        import time

        if key in self._data:
            value, expiry = self._data[key]
            if expiry is not None and time.time() > expiry:
                del self._data[key]
                return None
            return value
        return None

    async def setex(self, key, seconds, value):
        import time

        self._data[key] = (value, time.time() + seconds)

    async def delete(self, key):
        removed = 0
        if key in self._data:
            del self._data[key]
            removed += 1
        if key in self._hashes:
            del self._hashes[key]
            self._hash_expiry.pop(key, None)
            removed += 1
        if key in self._zsets:
            del self._zsets[key]
            self._zset_expiry.pop(key, None)
            removed += 1
        return removed

    def pipeline(self):
        return FakeRedisPipeline(self)

    def incr(self, key):
        import time

        if key not in self._data:
            self._data[key] = ("1", None)
        else:
            val, exp = self._data[key]
            self._data[key] = (str(int(val) + 1), exp)
        return int(self._data[key][0])

    async def expire(self, key, seconds):
        import time

        if key in self._data:
            val, _ = self._data[key]
            self._data[key] = (val, time.time() + seconds)
            return True
        if key in self._hashes:
            self._hash_expiry[key] = time.time() + seconds
            return True
        if key in self._zsets:
            self._zset_expiry[key] = time.time() + seconds
            return True
        return False

    async def hset(self, key, mapping):
        self._check_hash_expired(key)
        if key not in self._hashes:
            self._hashes[key] = {}
        for field, value in mapping.items():
            self._hashes[key][field] = value
        return len(mapping)

    async def hgetall(self, key):
        self._check_hash_expired(key)
        return self._hashes.get(key, {}).copy()

    async def hexists(self, key, field):
        self._check_hash_expired(key)
        return field in self._hashes.get(key, {})

    async def zadd(self, key, mapping):
        self._check_zset_expired(key)
        if key not in self._zsets:
            self._zsets[key] = {}
        for member, score in mapping.items():
            self._zsets[key][member] = float(score)
        return len(mapping)

    async def zrem(self, key, *members):
        self._check_zset_expired(key)
        if key not in self._zsets:
            return 0
        removed = 0
        for member in members:
            if member in self._zsets[key]:
                del self._zsets[key][member]
                removed += 1
        if not self._zsets.get(key):
            self._zsets.pop(key, None)
            self._zset_expiry.pop(key, None)
        return removed

    async def zremrangebyscore(self, key, min_score, max_score):
        self._check_zset_expired(key)
        if key not in self._zsets:
            return 0
        removed = 0
        min_val = float(min_score)
        max_val = float(max_score)
        to_remove = [m for m, s in self._zsets[key].items() if min_val <= s <= max_val]
        for m in to_remove:
            del self._zsets[key][m]
            removed += 1
        if not self._zsets.get(key):
            self._zsets.pop(key, None)
            self._zset_expiry.pop(key, None)
        return removed

    async def zcard(self, key):
        self._check_zset_expired(key)
        return len(self._zsets.get(key, {}))

    async def zrange(self, key, start, stop, withscores=False):
        self._check_zset_expired(key)
        if key not in self._zsets:
            return []
        items = sorted(self._zsets[key].items(), key=lambda x: x[1])
        total = len(items)
        if start < 0:
            start = max(0, total + start)
        if stop < 0:
            stop = total + stop
        else:
            stop = min(stop, total - 1)
        result = items[start : stop + 1]
        if withscores:
            return [[m, s] for m, s in result]
        return [m for m, s in result]

    async def exists(self, *keys):
        import time

        count = 0
        for key in keys:
            if key in self._data:
                value, expiry = self._data[key]
                if expiry is None or time.time() <= expiry:
                    count += 1
            elif key in self._hashes:
                if not self._check_hash_expired(key):
                    count += 1
            elif key in self._zsets:
                if not self._check_zset_expired(key):
                    count += 1
        return count

    async def ttl(self, key):
        import time

        if key in self._data:
            val, expiry = self._data[key]
            if expiry is None:
                return -1
            remaining = int(expiry - time.time())
            return remaining if remaining > 0 else -2
        if key in self._hashes:
            if key in self._hash_expiry:
                remaining = int(self._hash_expiry[key] - time.time())
                return remaining if remaining > 0 else -2
            return -1
        if key in self._zsets:
            if key in self._zset_expiry:
                remaining = int(self._zset_expiry[key] - time.time())
                return remaining if remaining > 0 else -2
            return -1
        return -2


@pytest.fixture(scope="session")
def postgres_url() -> Generator[str, None, None]:
    with PostgresContainer("postgres:15-alpine", driver="psycopg") as postgres:
        url = postgres.get_connection_url().replace(
            "postgresql+psycopg2://", "postgresql+psycopg://"
        )
        yield url


@pytest.fixture(scope="session", autouse=True)
def setup_database(postgres_url: str):
    sync_url = postgres_url.replace("postgresql+psycopg://", "postgresql+psycopg://")
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(alembic_cfg, "heads")
    yield
    engine = create_engine(sync_url)
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def async_engine(postgres_url: str) -> AsyncGenerator[AsyncEngine, None]:
    async_url = postgres_url.replace("postgresql+psycopg://", "postgresql+asyncpg://")
    engine = create_async_engine(async_url, poolclass=NullPool, future=True)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def db_session(async_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    async_session = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(loop_scope="session")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    fake_redis = FakeRedis()

    async def override_get_redis() -> FakeRedis:
        return fake_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis_client] = override_get_redis

    # Use very high rate limits during general test runs so existing tests are not blocked
    app.state.rate_limit_config = {
        "search": {"max_requests": 10000, "window_seconds": 60, "identifier_type": "ip"},
        "hold": {"max_requests": 10000, "window_seconds": 600, "identifier_type": "session"},
        "promo": {"max_requests": 10000, "window_seconds": 60, "identifier_type": "ip"},
        "booking": {"max_requests": 10000, "window_seconds": 300, "identifier_type": "session"},
        "login": {"max_requests": 10000, "window_seconds": 900, "identifier_type": "ip"},
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    del app.dependency_overrides[get_db]
    del app.dependency_overrides[get_redis_client]
    if hasattr(app.state, "rate_limit_config"):
        delattr(app.state, "rate_limit_config")
