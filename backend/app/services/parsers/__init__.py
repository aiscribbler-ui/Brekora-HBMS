"""OTA email parsers package."""

from app.services.parsers.airbnb_parser import AirbnbParser, ParsedBookingResult
from app.services.parsers.goibibo_parser import GoibiboParser
from app.services.parsers.mmt_parser import MMTParser

PARSER_MAP = {
    "airbnb": AirbnbParser,
    "mmt": MMTParser,
    "goibibo": GoibiboParser,
}

__all__ = [
    "AirbnbParser",
    "GoibiboParser",
    "MMTParser",
    "ParsedBookingResult",
    "PARSER_MAP",
]
