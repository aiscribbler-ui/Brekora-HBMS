import uuid
from decimal import Decimal

from sqlalchemy import Boolean, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import OrganizationMixin, TimestampMixin


class CancellationPolicy(Base, OrganizationMixin, TimestampMixin):
    __tablename__ = "cancellation_policy"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    free_cancellation_hours: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    partial_refund_hours: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    partial_refund_percentage: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    non_refundable_hours: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    is_non_refundable: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
