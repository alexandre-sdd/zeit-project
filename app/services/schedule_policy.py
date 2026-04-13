"""
Shared scheduling policy for the recruiter demo.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from math import ceil

WORKDAY_START_HOUR = 9
WORKDAY_END_HOUR = 17
WORKDAYS_PER_WEEK = 5
SLOT_MINUTES = 30
SLOTS_PER_DAY = ((WORKDAY_END_HOUR - WORKDAY_START_HOUR) * 60) // SLOT_MINUTES
TOTAL_WEEKLY_SLOTS = WORKDAYS_PER_WEEK * SLOTS_PER_DAY


def week_end_date(week_start: date) -> date:
    """Return the final day in the configured planning week."""
    return week_start + timedelta(days=WORKDAYS_PER_WEEK - 1)


def week_bounds(week_start: date) -> tuple[datetime, datetime]:
    """Return the inclusive planning window used by the scheduler."""
    week_start_at = datetime.combine(week_start, time(hour=WORKDAY_START_HOUR))
    week_end_at = datetime.combine(week_end_date(week_start), time(hour=WORKDAY_END_HOUR))
    return week_start_at, week_end_at


def slot_count(duration_minutes: int) -> int:
    """Round task duration up to the scheduler's slot granularity."""
    return max(1, ceil(duration_minutes / SLOT_MINUTES))
