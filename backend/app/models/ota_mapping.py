import uuid

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import OrganizationMixin, TimestampMixin


class OTAMapping(Base, OrganizationMixin, TimestampMixin):
    __tablename__ = "ota_mapping"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    ota_source: Mapped[str] = mapped_column(String(50), nullable=False)
    listing_id: Mapped[str] = mapped_column(String(255), nullable=False)
    room_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("room_type.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("property.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    room_type: Mapped["RoomType"] = relationship("RoomType", lazy="selectin")
    property: Mapped["Property"] = relationship("Property", lazy="selectin")

    __table_args__ = (
        UniqueConstraint(
            "org_id",
            "ota_source",
            "listing_id",
            name="uq_ota_mapping_org_source_listing",
        ),
    )
