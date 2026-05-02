import uuid
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import OrganizationMixin, TimestampMixin


class Package(Base, OrganizationMixin, TimestampMixin):
    __tablename__ = "package"

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
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    base_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    dynamic_pricing_rules: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=dict
    )
    date_constraints: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=dict
    )
    max_occupancy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cancellation_policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    compositions: Mapped[list["PackageComposition"]] = relationship(
        "PackageComposition",
        back_populates="package",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    add_ons: Mapped[list["PackageAddOn"]] = relationship(
        "PackageAddOn",
        back_populates="package",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class PackageComposition(Base, OrganizationMixin, TimestampMixin):
    __tablename__ = "package_composition"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("package.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    room_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("room_type.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    nights: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    package: Mapped["Package"] = relationship("Package", back_populates="compositions")
    room_type: Mapped["RoomType"] = relationship("RoomType", back_populates="package_compositions")


class PackageAddOn(Base, OrganizationMixin, TimestampMixin):
    __tablename__ = "package_add_on"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("package.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    add_on_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("add_on.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_included: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    package: Mapped["Package"] = relationship("Package", back_populates="add_ons")
    add_on: Mapped["AddOn"] = relationship("AddOn", back_populates="package_add_ons", lazy="selectin")
