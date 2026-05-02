import uuid
from decimal import Decimal
from enum import Enum

from sqlalchemy import Boolean, Enum as SAEnum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import OrganizationMixin, TimestampMixin


class AddOnType(str, Enum):
    slot = "slot"
    day = "day"
    package_instance = "package_instance"


class AddOn(Base, OrganizationMixin, TimestampMixin):
    __tablename__ = "add_on"

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
    type: Mapped[AddOnType] = mapped_column(
        SAEnum(AddOnType, native_enum=False, create_type=False),
        nullable=False,
        default=AddOnType.day,
    )
    default_capacity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    capacities: Mapped[list["AddOnCapacity"]] = relationship(
        "AddOnCapacity",
        back_populates="add_on",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    package_add_ons: Mapped[list["PackageAddOn"]] = relationship(
        "PackageAddOn",
        back_populates="add_on",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
