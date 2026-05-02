import uuid
from datetime import date

from sqlalchemy import Date, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin


class ParseMetric(Base, TimestampMixin):
    __tablename__ = "parse_metric"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    ota_source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    total_parsed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    successful: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    failed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    avg_confidence: Mapped[float] = mapped_column(
        Numeric(4, 3),
        default=0.0,
        nullable=False,
    )
    date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
