import uuid
from decimal import Decimal

from pydantic import BaseModel


class AlternativeSuggestion(BaseModel):
    item_type: str  # "room" or "package"
    item_id: uuid.UUID
    item_name: str
    available_count: int
    suggested_price: Decimal
    currency: str


class BookingConflictResponse(BaseModel):
    detail: str
    alternatives: list[AlternativeSuggestion]
