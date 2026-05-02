import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, model_validator


class ParsedBookingQueueBase(BaseModel):
    source_type: str
    raw_email_id: Optional[uuid.UUID] = None
    ota_reference_id: Optional[str] = None
    parsed_data: Optional[dict[str, Any]] = None
    confidence_score: Decimal = Decimal("0.000")
    status: str = "pending"
    review_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    confirmed_booking_id: Optional[uuid.UUID] = None


class ParsedBookingQueueCreate(ParsedBookingQueueBase):
    org_id: Optional[uuid.UUID] = None


class ParsedBookingQueueUpdate(BaseModel):
    source_type: Optional[str] = None
    raw_email_id: Optional[uuid.UUID] = None
    ota_reference_id: Optional[str] = None
    parsed_data: Optional[dict[str, Any]] = None
    confidence_score: Optional[Decimal] = None
    status: Optional[str] = None
    manager_id: Optional[uuid.UUID] = None
    review_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    confirmed_booking_id: Optional[uuid.UUID] = None


class ParsedBookingQueueRead(ParsedBookingQueueBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    manager_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    # Fields extracted from parsed_data for frontend compatibility
    property_id: Optional[uuid.UUID] = None
    guest_name: Optional[str] = None
    guest_email: Optional[str] = None
    guest_phone: Optional[str] = None
    check_in: Optional[date] = None
    check_out: Optional[date] = None
    num_guests: Optional[int] = None
    room_type: Optional[str] = None
    ota_reference: Optional[str] = None

    @model_validator(mode='before')
    @classmethod
    def _extract_parsed_data(cls, data: Any) -> Any:
        if hasattr(data, '__table__'):
            parsed = getattr(data, 'parsed_data', None) or {}
            d = {col.name: getattr(data, col.name) for col in data.__table__.columns}
            d['property_id'] = parsed.get('property_id')
            d['guest_name'] = parsed.get('guest_name')
            d['guest_email'] = parsed.get('guest_email')
            d['guest_phone'] = parsed.get('guest_phone')
            d['check_in'] = parsed.get('check_in')
            d['check_out'] = parsed.get('check_out')
            d['num_guests'] = parsed.get('number_of_guests')
            d['room_type'] = parsed.get('room_type')
            d['ota_reference'] = d.get('ota_reference_id')
            return d
        if isinstance(data, dict):
            parsed = data.get('parsed_data') or {}
            data.setdefault('property_id', parsed.get('property_id'))
            data.setdefault('guest_name', parsed.get('guest_name'))
            data.setdefault('guest_email', parsed.get('guest_email'))
            data.setdefault('guest_phone', parsed.get('guest_phone'))
            data.setdefault('check_in', parsed.get('check_in'))
            data.setdefault('check_out', parsed.get('check_out'))
            data.setdefault('num_guests', parsed.get('number_of_guests'))
            data.setdefault('room_type', parsed.get('room_type'))
            data.setdefault('ota_reference', data.get('ota_reference_id'))
            return data
        return data


class ParsedBookingQueueConfirmRequest(BaseModel):
    room_type_id: Optional[uuid.UUID] = None
    property_id: Optional[uuid.UUID] = None
    check_in: Optional[date] = None
    check_out: Optional[date] = None
    guest_name: Optional[str] = None
    guest_email: Optional[str] = None
    number_of_guests: Optional[int] = None
    gross_amount: Optional[Decimal] = None
    net_payout: Optional[Decimal] = None


class ParsedBookingQueueEditRequest(BaseModel):
    ota_reference_id: Optional[str] = None
    guest_name: Optional[str] = None
    guest_email: Optional[str] = None
    check_in: Optional[date] = None
    check_out: Optional[date] = None
    number_of_guests: Optional[int] = None
    gross_amount: Optional[Decimal] = None
    net_payout: Optional[Decimal] = None
    review_notes: Optional[str] = None
    parsed_data: Optional[dict[str, Any]] = None


class ParsedBookingQueueRejectRequest(BaseModel):
    rejection_reason: str
