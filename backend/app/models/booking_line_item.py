# BookingLineItem is defined in booking.py to avoid circular imports
# Re-export for convenience
from app.models.booking import BookingLineItem

__all__ = ["BookingLineItem"]
