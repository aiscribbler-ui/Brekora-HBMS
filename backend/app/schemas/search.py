from datetime import date
from decimal import Decimal
from typing import Any
import uuid

from pydantic import BaseModel

from app.schemas.pricing import PriceBreakdown


class PropertySnippet(BaseModel):
    id: uuid.UUID
    name: str
    address: str | None = None
    photos: list[dict[str, Any]] | None = None
    amenities: list[str] | None = None


class SearchRequest(BaseModel):
    location: str
    check_in: date
    check_out: date
    guests: int
    promo_code: str | None = None


class SearchResultItem(BaseModel):
    type: str  # "room" or "package"
    id: uuid.UUID
    name: str
    photos: list[dict[str, Any]] | None = None
    description: str | None = None
    available: bool
    price_breakdown: PriceBreakdown
    property: PropertySnippet


class SearchResponse(BaseModel):
    results: list[SearchResultItem]
