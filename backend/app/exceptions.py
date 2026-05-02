class InventoryError(Exception):
    """Raised for general inventory-related failures."""


class ConflictError(InventoryError):
    """Raised when a concurrent booking conflict is detected."""


class BookingConflictError(ValueError):
    """Raised when a booking cannot be initialized due to inventory unavailability.

    Carries alternative suggestions so the API can return a friendly 409.
    """

    def __init__(self, message: str, alternatives: list[dict] | None = None):
        super().__init__(message)
        self.alternatives = alternatives or []
