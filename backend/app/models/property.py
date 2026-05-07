import uuid
from datetime import time
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text, Time
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import OrganizationMixin, TimestampMixin


class Property(Base, OrganizationMixin, TimestampMixin):
    __tablename__ = "property"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    gstin: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pan: Mapped[str | None] = mapped_column(String(50), nullable=True)
    owner_contact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 8), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(11, 8), nullable=True)
    photos: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True, default=list)
    amenities: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True, default=list)
    default_check_in_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    default_check_out_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    cancellation_policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    room_types: Mapped[list["RoomType"]] = relationship(
        "RoomType",
        back_populates="property",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    inventory_buffers: Mapped[list["InventoryBuffer"]] = relationship(
        "InventoryBuffer",
        back_populates="property",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    users: Mapped[list["User"]] = relationship(
        "User",
        secondary="user_property",
        back_populates="properties",
        lazy="selectin",
    )
