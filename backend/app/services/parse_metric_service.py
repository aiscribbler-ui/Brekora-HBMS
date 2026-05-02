import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.parse_metric import ParseMetric
from app.repositories.parse_metric import ParseMetricRepository

logger = logging.getLogger(__name__)


class ParseMetricService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ParseMetricRepository(session)

    async def record_parse(
        self, ota_source: str, success: bool, confidence: float
    ) -> ParseMetric:
        today = date.today()
        metric = await self.repo.get_by_date_and_source(today, ota_source)
        if not metric:
            metric = await self.repo.create(
                {
                    "ota_source": ota_source,
                    "date": today,
                    "total_parsed": 0,
                    "successful": 0,
                    "failed": 0,
                    "avg_confidence": 0.0,
                }
            )

        total_parsed = metric.total_parsed + 1
        successful = metric.successful + (1 if success else 0)
        failed = metric.failed + (0 if success else 1)

        current_avg = Decimal(str(metric.avg_confidence))
        new_confidence = Decimal(str(confidence))
        new_avg = (
            current_avg * Decimal(metric.total_parsed) + new_confidence
        ) / Decimal(total_parsed)

        metric = await self.repo.update(
            metric,
            {
                "total_parsed": total_parsed,
                "successful": successful,
                "failed": failed,
                "avg_confidence": float(new_avg),
            },
        )
        return metric

    async def get_metrics(
        self, start_date: date, end_date: date, ota_source: str | None = None
    ) -> list[dict[str, Any]]:
        stmt = (
            select(ParseMetric)
            .where(ParseMetric.date >= start_date)
            .where(ParseMetric.date <= end_date)
        )
        if ota_source:
            stmt = stmt.where(ParseMetric.ota_source == ota_source)
        stmt = stmt.order_by(ParseMetric.date, ParseMetric.ota_source)
        result = await self.session.execute(stmt)
        metrics = result.scalars().all()
        return [
            {
                "id": str(m.id),
                "ota_source": m.ota_source,
                "date": m.date.isoformat(),
                "total_parsed": m.total_parsed,
                "successful": m.successful,
                "failed": m.failed,
                "avg_confidence": float(m.avg_confidence),
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "updated_at": m.updated_at.isoformat() if m.updated_at else None,
            }
            for m in metrics
        ]

    async def get_accuracy(self, ota_source: str, days: int = 30) -> float:
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        stmt = select(
            func.coalesce(func.sum(ParseMetric.total_parsed), 0).label("total"),
            func.coalesce(func.sum(ParseMetric.successful), 0).label("successful"),
        ).where(ParseMetric.date >= start_date).where(ParseMetric.date <= end_date)

        if ota_source:
            stmt = stmt.where(ParseMetric.ota_source == ota_source)

        result = await self.session.execute(stmt)
        row = result.one()
        total = row.total or 0
        successful = row.successful or 0
        if total == 0:
            return 0.0
        return float(successful) / float(total)
