import uuid

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import OrganizationMixin, TimestampMixin


class RoomType(Base, OrganizationMixin, TimestampMixin):
    __tablename__ = "room_type"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("property.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    base_capacity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_capacity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    default_rate: Mapped[float] = mapped_column(Numeric(12, 2), default=0.00, nullable=False)
    min_stay: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_stay: Mapped[int | None] = mapped_column(Integer, nullable=True)
    photos: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    property: Mapped["Property"] = relationship("Property", back_populates="room_types")
    package_compositions: Mapped[list["PackageComposition"]] = relationship(
        "PackageComposition",
        back_populates="room_type",
        lazy="selectin",
    )
    inventory_buffers: Mapped[list["InventoryBuffer"]] = relationship(
        "InventoryBuffer",
        back_populates="room_type",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
