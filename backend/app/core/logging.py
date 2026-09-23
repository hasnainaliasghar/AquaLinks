"""Centralized logging configuration."""

from __future__ import annotations

import logging
import sys
from logging.config import dictConfig


def configure_logging(level: str = "INFO") -> None:
    """Configure root and uvicorn loggers to use a consistent format."""
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)-7s %(name)s :: %(message)s",
                    "datefmt": "%H:%M:%S",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "stream": sys.stdout,
                    "formatter": "default",
                }
            },
            "root": {"handlers": ["console"], "level": level},
            "loggers": {
                "uvicorn.error": {"level": level, "handlers": ["console"], "propagate": False},
                "uvicorn.access": {"level": "WARNING", "handlers": ["console"], "propagate": False},
                "sqlalchemy.engine": {"level": "WARNING"},
                # WeasyPrint emits hundreds of "Ignored ... unknown property"
                # warnings when ingesting matplotlib's SVG output (matplotlib
                # writes `fill="…"` as XML attributes, not CSS — WeasyPrint
                # complains but renders correctly). Quiet these so real
                # errors stay visible.
                "weasyprint": {"level": "ERROR"},
                "fontTools": {"level": "ERROR"},
                "fontTools.subset": {"level": "ERROR"},
                "fontTools.ttLib": {"level": "ERROR"},
            },
        }
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
