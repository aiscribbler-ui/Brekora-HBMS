import time
import uuid

from redis.asyncio import Redis


class SessionService:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def create_session(
        self,
        user_id: str,
        role: str,
        ip: str | None,
        user_agent: str | None,
    ) -> str:
        session_id = str(uuid.uuid4())
        now = time.time()

        ttl = 28800 if role in ("Admin", "Manager") else 2592000  # 8h vs 30d

        await self.redis.hset(
            f"session:{session_id}",
            mapping={
                "user_id": user_id,
                "role": role,
                "ip": ip or "",
                "user_agent": user_agent or "",
                "created_at": str(now),
                "last_activity": str(now),
            },
        )
        await self.redis.expire(f"session:{session_id}", ttl)
        await self.redis.zadd(f"sessions:{user_id}", {session_id: now})
        return session_id

    async def validate_session(self, session_id: str) -> bool:
        exists = await self.redis.exists(f"session:{session_id}")
        if not exists:
            return False
        now = str(time.time())
        await self.redis.hset(f"session:{session_id}", mapping={"last_activity": now})
        return True

    async def get_session(self, session_id: str) -> dict | None:
        data = await self.redis.hgetall(f"session:{session_id}")
        if not data:
            return None
        return data

    async def list_sessions(self, user_id: str) -> list[dict]:
        session_ids = await self.redis.zrange(f"sessions:{user_id}", 0, -1)
        sessions = []
        for sid in session_ids:
            data = await self.redis.hgetall(f"session:{sid}")
            if data:
                sessions.append(
                    {
                        "session_id": sid,
                        "user_id": data.get("user_id"),
                        "role": data.get("role"),
                        "ip": data.get("ip"),
                        "user_agent": data.get("user_agent"),
                        "created_at": data.get("created_at"),
                        "last_activity": data.get("last_activity"),
                    }
                )
            else:
                await self.redis.zrem(f"sessions:{user_id}", sid)
        return sessions

    async def terminate_session(self, session_id: str) -> bool:
        data = await self.redis.hgetall(f"session:{session_id}")
        if not data:
            return False
        user_id = data.get("user_id")
        await self.redis.delete(f"session:{session_id}")
        if user_id:
            await self.redis.zrem(f"sessions:{user_id}", session_id)
        return True

    async def terminate_all_sessions(
        self, user_id: str, except_session_id: str | None = None
    ) -> int:
        session_ids = await self.redis.zrange(f"sessions:{user_id}", 0, -1)
        removed = 0
        for sid in session_ids:
            if except_session_id and sid == except_session_id:
                continue
            await self.redis.delete(f"session:{sid}")
            await self.redis.zrem(f"sessions:{user_id}", sid)
            removed += 1
        return removed

    async def evict_oldest_session(self, user_id: str) -> bool:
        session_ids = await self.redis.zrange(f"sessions:{user_id}", 0, 0)
        if not session_ids:
            return False
        oldest = session_ids[0]
        return await self.terminate_session(oldest)

    async def check_concurrent_limit(
        self, user_id: str, role: str, max_sessions: int = 3
    ) -> bool:
        if role == "Guest":
            return True
        sessions = await self.list_sessions(user_id)
        if len(sessions) < max_sessions:
            return True
        # At limit: evict the oldest session to make room
        await self.evict_oldest_session(user_id)
        return True
