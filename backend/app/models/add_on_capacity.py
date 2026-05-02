import uuid
from datetime import date, time

from sqlalchemy import Date, ForeignKey, Integer, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin
from app.models.add_on import AddOn


class AddOnCapacity(Base, TimestampMixin):
    __tablename__ = "add_on_capacity"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    add_on_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("add_on.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    slot_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    available_capacity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_capacity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    add_on: Mapped[AddOn] = relationship("AddOn", back_populates="capacities")
