import uuid

from sqlalchemy import Boolean, Float, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import OrganizationMixin, TimestampMixin


class OTASettings(Base, OrganizationMixin, TimestampMixin):
    __tablename__ = "ota_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    ota_source: Mapped[str] = mapped_column(String(50), nullable=False)
    auto_confirm: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    min_confidence: Mapped[float] = mapped_column(
        Float, default=0.95, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "org_id",
            "ota_source",
            name="uq_ota_settings_org_source",
        ),
    )
