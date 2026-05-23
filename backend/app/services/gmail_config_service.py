"""Service for reading Gmail OAuth credentials from system config."""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.system_config import SystemConfigRepository


class GmailConfigService:
    """Read / write Gmail OAuth client credentials and redirect URI from system_config.

    Falls back to environment variables if no DB entry exists.
    """

    def __init__(
        self,
        session: AsyncSession,
        org_id: uuid.UUID,
        env_client_id: str,
        env_client_secret: str,
        env_redirect_uri: str = "",
    ):
        self.session = session
        self.org_id = org_id
        self._env_client_id = env_client_id
        self._env_client_secret = env_client_secret
        self._env_redirect_uri = env_redirect_uri

    async def get_credentials(self) -> dict[str, str | None]:
        repo = SystemConfigRepository(self.session, self.org_id)
        client_id_cfg = await repo.get_by_key("gmail_client_id")
        client_secret_cfg = await repo.get_by_key("gmail_client_secret")
        return {
            "client_id": (client_id_cfg.value if client_id_cfg else None) or self._env_client_id or None,
            "client_secret": (client_secret_cfg.value if client_secret_cfg else None) or self._env_client_secret or None,
        }

    async def get_redirect_uri(self) -> str | None:
        repo = SystemConfigRepository(self.session, self.org_id)
        cfg = await repo.get_by_key("gmail_redirect_uri")
        return (cfg.value if cfg else None) or self._env_redirect_uri or None

    async def is_configured(self) -> bool:
        creds = await self.get_credentials()
        return bool(creds.get("client_id") and creds.get("client_secret"))

    async def set_credentials(self, client_id: str, client_secret: str) -> None:
        repo = SystemConfigRepository(self.session, self.org_id)

        client_id_cfg = await repo.get_by_key("gmail_client_id")
        if client_id_cfg is None:
            await repo.create({"key": "gmail_client_id", "value": client_id, "data_type": "string"})
        else:
            await repo.update(client_id_cfg, {"value": client_id})

        client_secret_cfg = await repo.get_by_key("gmail_client_secret")
        if client_secret_cfg is None:
            await repo.create({"key": "gmail_client_secret", "value": client_secret, "data_type": "string"})
        else:
            await repo.update(client_secret_cfg, {"value": client_secret})

    async def set_redirect_uri(self, redirect_uri: str) -> None:
        repo = SystemConfigRepository(self.session, self.org_id)
        cfg = await repo.get_by_key("gmail_redirect_uri")
        if cfg is None:
            await repo.create({"key": "gmail_redirect_uri", "value": redirect_uri, "data_type": "string"})
        else:
            await repo.update(cfg, {"value": redirect_uri})
