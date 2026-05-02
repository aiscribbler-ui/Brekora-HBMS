from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class GSTBreakdown(BaseModel):
    taxable_value: Decimal
    gst_amount: Decimal
    total: Decimal
    rate: Decimal


class GSTRateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    value: str
    data_type: str
