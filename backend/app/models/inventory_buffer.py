import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import OrganizationMixin, TimestampMixin


class InventoryBuffer(Base, OrganizationMixin, TimestampMixin):
    __tablename__ = "inventory_buffer"

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
    room_type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("room_type.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    buffer_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    property: Mapped["Property"] = relationship("Property", back_populates="inventory_buffers")
    room_type: Mapped["RoomType | None"] = relationship("RoomType", back_populates="inventory_buffers")

    __table_args__ = (
        UniqueConstraint("org_id", "property_id", "room_type_id", "date", name="uq_buffer_org_room_date"),
    )
