"""Centralised JSON logging configuration."""
import logging.config
import sys

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "fmt": "%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": sys.stdout,
        }
    },
    "loggers": {
        "uvicorn": {"handlers": ["console"], "level": "INFO"},
        "uvicorn.access": {"handlers": ["console"], "level": "INFO"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}


def setup_logging() -> None:
    logging.config.dictConfig(LOGGING_CONFIG)
