import uuid

from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import OrganizationMixin, TimestampMixin


class SystemConfig(Base, OrganizationMixin, TimestampMixin):
    __tablename__ = "system_config"
    __table_args__ = (UniqueConstraint("org_id", "key", name="uq_system_config_org_key"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    data_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="string"
    )
