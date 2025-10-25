"""
Logging configuration helpers.

Expose a convenience function to configure structural logging across the
application. Keeping it centralized allows both the API layer and CLI
tools to share the configuration.
"""
from __future__ import annotations

import logging
from typing import Literal

LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)


def configure_logging(level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO") -> None:
    """Configure the root logger with a consistent format."""
    logging.basicConfig(level=level, format=LOG_FORMAT)
