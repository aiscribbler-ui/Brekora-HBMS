import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import OrganizationMixin, TimestampMixin


class BookingType(PyEnum):
    room = "room"
    package = "package"


class SourceType(PyEnum):
    direct = "direct"
    manual = "manual"
    gmail_airbnb = "gmail_airbnb"
    gmail_mmt = "gmail_mmt"
    gmail_goibibo = "gmail_goibibo"
    ical = "ical"


class BookingStatus(PyEnum):
    pending_payment = "pending_payment"
    confirmed = "confirmed"
    payment_failed = "payment_failed"
    cancelled = "cancelled"
    completed = "completed"


class Booking(Base, OrganizationMixin, TimestampMixin):
    __tablename__ = "booking"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    booking_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=SourceType.direct.value,
    )
    source_reference: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("property.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    guest_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    check_in: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    check_out: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=BookingStatus.pending_payment.value,
        index=True,
    )
    line_items: Mapped[list[dict] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
    )
    gross_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="INR"
    )
    cancellation_policy_snapshot: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=dict
    )
    partner_attribution_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    payment_state: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    idempotency_key: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    notes: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancellation_reason: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    modification_log: Mapped[list[dict] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
    )

    line_item_records: Mapped[list["BookingLineItem"]] = relationship(
        "BookingLineItem",
        back_populates="booking",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    payments: Mapped[list["Payment"]] = relationship(
        "Payment",
        back_populates="booking",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint(
            "org_id", "idempotency_key", name="uq_booking_org_idempotency"
        ),
    )


class BookingLineItem(Base, TimestampMixin):
    __tablename__ = "booking_line_item"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("booking.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(
        default=1, nullable=False
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    nights: Mapped[int] = mapped_column(
        default=1, nullable=False
    )
    total_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )

    booking: Mapped["Booking"] = relationship("Booking", back_populates="line_item_records")
