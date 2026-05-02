import uuid
from datetime import date

from sqlalchemy import select

from app.models.parse_metric import ParseMetric
from app.repositories.base import BaseRepository


class ParseMetricRepository(BaseRepository[ParseMetric]):
    @property
    def model_class(self) -> type[ParseMetric]:
        return ParseMetric

    async def get_by_date_and_source(
        self, metric_date: date, ota_source: str
    ) -> ParseMetric | None:
        stmt = (
            select(ParseMetric)
            .where(ParseMetric.date == metric_date)
            .where(ParseMetric.ota_source == ota_source)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
