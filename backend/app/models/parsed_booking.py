import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import OrganizationMixin, TimestampMixin


class ParsedBookingStatus(PyEnum):
    pending = "pending"
    confirmed = "confirmed"
    rejected = "rejected"
    failed = "failed"


class ParsedBookingQueue(Base, OrganizationMixin, TimestampMixin):
    __tablename__ = "parsed_booking_queue"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    raw_email_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("raw_email.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ota_reference_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    parsed_data: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
    )
    confidence_score: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        default=Decimal("0.000"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ParsedBookingStatus.pending.value,
        index=True,
    )
    manager_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    review_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    confirmed_booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("booking.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    raw_email: Mapped["RawEmail"] = relationship("RawEmail", lazy="selectin")
    manager: Mapped["User"] = relationship("User", lazy="selectin")
    confirmed_booking: Mapped["Booking"] = relationship("Booking", lazy="selectin")

    __table_args__ = (
        {
            "comment": "Queue of parsed OTA bookings awaiting manager review",
        },
    )
