import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class ParseMetricRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ota_source: str
    date: date
    total_parsed: int
    successful: int
    failed: int
    avg_confidence: float
    created_at: datetime
    updated_at: datetime
