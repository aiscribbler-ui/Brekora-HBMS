import uuid
from datetime import datetime, timezone

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_temp_token,
    decode_refresh_token,
    decode_temp_token,
    verify_password,
)
from app.models.user import User
from app.repositories.user import UserRepository
from app.services.session_service import SessionService
from app.services.totp_service import TOTPService


class AuthService:
    def __init__(self, db: AsyncSession | None, redis_client: Redis):
        self.db = db
        self.redis = redis_client
        self.session_service = SessionService(redis_client)

    async def login(
        self,
        email: str,
        password: str,
        org_id: uuid.UUID,
        ip: str | None,
        user_agent: str | None,
    ) -> dict:
        repo = UserRepository(self.db, org_id)
        user = await repo.get_by_email(email)
        if not user or not user.is_active:
            raise ValueError("Invalid credentials")
        if not verify_password(password, user.password_hash):
            raise ValueError("Invalid credentials")

        if user.is_2fa_enabled:
            temp_token = create_temp_token(user.id, user.org_id)
            return {
                "access_token": None,
                "refresh_token": None,
                "token_type": "bearer",
                "expires_in": None,
                "temp_token": temp_token,
                "requires_2fa": True,
                "session_id": None,
            }

        role_name = user.role.name if user.role else "Guest"
        if not await self.session_service.check_concurrent_limit(
            str(user.id), role_name
        ):
            raise ValueError("Maximum concurrent sessions reached")

        return await self._issue_tokens_and_session(user, ip, user_agent)

    async def _issue_tokens_and_session(
        self, user: User, ip: str | None, user_agent: str | None
    ) -> dict:
        role_name = user.role.name if user.role else "Guest"
        name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        access_token = create_access_token(
            user.id, user.org_id, role=role_name, email=user.email, name=name or None
        )
        refresh_jti = uuid.uuid4()
        refresh_token = create_refresh_token(user.id, user.org_id, refresh_jti)

        settings = get_settings()
        ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        await self.redis.setex(f"refresh:{refresh_jti}", ttl, str(user.id))

        session_id = await self.session_service.create_session(
            user_id=str(user.id),
            role=role_name,
            ip=ip,
            user_agent=user_agent,
        )

        user.last_login = datetime.now(timezone.utc)
        await self.db.flush()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "temp_token": None,
            "requires_2fa": False,
            "session_id": session_id,
        }

    async def refresh(self, refresh_token: str) -> dict:
        payload = decode_refresh_token(refresh_token)
        if not payload:
            raise ValueError("Invalid refresh token")

        jti = payload.get("jti")
        user_id_str = payload.get("sub")
        org_id_str = payload.get("org_id")
        if not jti or not user_id_str or not org_id_str:
            raise ValueError("Invalid refresh token")

        stored_user_id = await self.redis.get(f"refresh:{jti}")
        if not stored_user_id or stored_user_id != user_id_str:
            raise ValueError("Invalid refresh token")

        await self.redis.delete(f"refresh:{jti}")

        user_id = uuid.UUID(user_id_str)
        org_id = uuid.UUID(org_id_str)

        role_name = None
        email = None
        name = None
        if self.db:
            from app.repositories.user import UserRepository
            repo = UserRepository(self.db, org_id)
            user = await repo.get(user_id)
            if user:
                role_name = user.role.name if user.role else "Guest"
                email = user.email
                name = f"{user.first_name or ''} {user.last_name or ''}".strip() or None

        access_token = create_access_token(user_id, org_id, role=role_name, email=email, name=name)
        new_refresh_jti = uuid.uuid4()
        new_refresh_token = create_refresh_token(user_id, org_id, new_refresh_jti)

        settings = get_settings()
        ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        await self.redis.setex(f"refresh:{new_refresh_jti}", ttl, str(user_id))

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "session_id": None,
        }

    async def logout(self, refresh_token: str, session_id: str | None) -> None:
        payload = decode_refresh_token(refresh_token)
        if payload:
            jti = payload.get("jti")
            if jti:
                await self.redis.delete(f"refresh:{jti}")
        if session_id:
            await self.session_service.terminate_session(session_id)

    async def login_verify_2fa(
        self,
        temp_token: str,
        token: str,
        ip: str | None,
        user_agent: str | None,
    ) -> dict:
        payload = decode_temp_token(temp_token)
        if not payload:
            raise ValueError("Invalid or expired temp token")

        user_id_str = payload.get("sub")
        org_id_str = payload.get("org_id")
        if not user_id_str or not org_id_str:
            raise ValueError("Invalid temp token payload")

        user_id = uuid.UUID(user_id_str)
        org_id = uuid.UUID(org_id_str)

        repo = UserRepository(self.db, org_id)
        user = await repo.get(user_id)
        if not user or not user.is_active or not user.is_2fa_enabled:
            raise ValueError("Invalid credentials")

        if not user.totp_secret or not TOTPService.verify_token(user.totp_secret, token):
            raise ValueError("Invalid TOTP token")

        role_name = user.role.name if user.role else "Guest"
        if not await self.session_service.check_concurrent_limit(
            str(user.id), role_name
        ):
            raise ValueError("Maximum concurrent sessions reached")

        return await self._issue_tokens_and_session(user, ip, user_agent)
