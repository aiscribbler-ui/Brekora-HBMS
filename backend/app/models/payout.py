import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import OrganizationMixin, TimestampMixin


class PayoutStatus:
    pending = "pending"
    paid = "paid"
    hold = "hold"


class Payout(Base, OrganizationMixin, TimestampMixin):
    __tablename__ = "payout"

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
    month: Mapped[str] = mapped_column(
        String(7),
        nullable=False,
        index=True,
    )
    gross_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    ota_commission: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    partner_commission: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    gst_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    net_distributable: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    owner_share: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    brekora_share: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    owner_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("70.00"), nullable=False
    )
    brekora_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("30.00"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=PayoutStatus.pending,
    )
