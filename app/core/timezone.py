"""
Timezone utilities for the Zeit project.

Encapsulates conversion helpers so the rest of the codebase can rely on
aware datetimes without handling zoneinfo details everywhere.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.settings import get_settings


def default_timezone() -> ZoneInfo:
    """Return the project's configured timezone."""
    return ZoneInfo(get_settings().timezone)


def to_local(dt: datetime) -> datetime:
    """Convert a naive or UTC datetime into the configured timezone."""
    tz = default_timezone()
    if dt.tzinfo is None:
        return dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz)
    return dt.astimezone(tz)
