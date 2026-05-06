import uuid
from datetime import date, time

from pydantic import BaseModel


class RoomAvailabilityNight(BaseModel):
    room_type_id: uuid.UUID
    date: date
    available_count: int
    total_count: int
    booked_count: int
    held_count: int


class RoomAvailabilityResponse(BaseModel):
    nights: list[RoomAvailabilityNight]


class AddOnAvailabilitySlot(BaseModel):
    date: date
    slot_time: time | None
    available_capacity: int
    total_capacity: int
    booked_count: int
    held_count: int


class AddOnAvailabilityDay(BaseModel):
    date: date
    available_capacity: int
    total_capacity: int
    booked_count: int
    held_count: int


class AddOnAvailabilityResponse(BaseModel):
    items: list[AddOnAvailabilitySlot | AddOnAvailabilityDay]
