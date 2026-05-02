from redis.asyncio import Redis

from app.core.config import get_settings

_redis_pool: Redis | None = None


async def get_redis() -> Redis:
    global _redis_pool
    if _redis_pool is None:
        settings = get_settings()
        _redis_pool = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_pool


async def get_redis_client() -> Redis:
    return await get_redis()
