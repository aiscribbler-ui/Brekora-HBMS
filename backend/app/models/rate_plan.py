import uuid
from decimal import Decimal

from sqlalchemy import Boolean, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import OrganizationMixin, TimestampMixin


class RatePlan(Base, OrganizationMixin, TimestampMixin):
    __tablename__ = "rate_plan"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    discount_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="percentage"
    )
    discount_value: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    min_nights: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_nights: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("org_id", "code", name="uq_rate_plan_org_code"),
    )
