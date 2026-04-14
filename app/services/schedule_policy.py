"""
Shared scheduling policy for the visitor demo.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from math import ceil

SLOT_MINUTES = 30
WORKDAY_START_HOUR = 9
WORKDAY_END_HOUR = 17
WORKDAY_START_MINUTES = WORKDAY_START_HOUR * 60
WORKDAY_END_MINUTES = WORKDAY_END_HOUR * 60
WORKDAYS_PER_WEEK = 5


@dataclass(frozen=True, slots=True)
class WorkdayWindow:
    start_minutes: int
    end_minutes: int

    def __post_init__(self) -> None:
        if self.start_minutes < 0 or self.end_minutes >= 24 * 60:
            raise ValueError("Workday times must stay within a single day")
        if self.start_minutes >= self.end_minutes:
            raise ValueError("`workday_start` must be earlier than `workday_end`")
        if self.start_minutes % SLOT_MINUTES != 0 or self.end_minutes % SLOT_MINUTES != 0:
            raise ValueError(f"Workday times must align to {SLOT_MINUTES}-minute slots")

    @property
    def start_time(self) -> time:
        return time(hour=self.start_minutes // 60, minute=self.start_minutes % 60)

    @property
    def end_time(self) -> time:
        return time(hour=self.end_minutes // 60, minute=self.end_minutes % 60)

    @property
    def slots_per_day(self) -> int:
        return (self.end_minutes - self.start_minutes) // SLOT_MINUTES

    @property
    def total_weekly_slots(self) -> int:
        return WORKDAYS_PER_WEEK * self.slots_per_day


def minutes_to_time_value(minutes: int) -> str:
    """Format minute offsets as an HTML-friendly `HH:MM` value."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def time_to_minutes(value: time) -> int:
    """Convert a time-of-day into minutes from midnight."""
    return value.hour * 60 + value.minute


def default_workday_window() -> WorkdayWindow:
    """Return the app's default workday window."""
    return WorkdayWindow(start_minutes=WORKDAY_START_MINUTES, end_minutes=WORKDAY_END_MINUTES)


def resolve_workday_window(
    *,
    workday_start: time | None = None,
    workday_end: time | None = None,
) -> WorkdayWindow:
    """Resolve request overrides against the app's default workday window."""
    default_window = default_workday_window()
    return WorkdayWindow(
        start_minutes=time_to_minutes(workday_start) if workday_start is not None else default_window.start_minutes,
        end_minutes=time_to_minutes(workday_end) if workday_end is not None else default_window.end_minutes,
    )


def workday_time_labels(workday_window: WorkdayWindow) -> list[str]:
    """Build human-readable time labels for the calendar rail."""
    labels = [minutes_to_time_value(workday_window.start_minutes)]
    next_minutes = workday_window.start_minutes + 60
    while next_minutes < workday_window.end_minutes:
        labels.append(minutes_to_time_value(next_minutes))
        next_minutes += 60
    end_label = minutes_to_time_value(workday_window.end_minutes)
    if labels[-1] != end_label:
        labels.append(end_label)
    return labels


def week_end_date(week_start: date) -> date:
    """Return the final day in the configured planning week."""
    return week_start + timedelta(days=WORKDAYS_PER_WEEK - 1)


def week_bounds(week_start: date) -> tuple[datetime, datetime]:
    """Return the full weekday range covered by the planning week."""
    week_start_at = datetime.combine(week_start, time.min)
    week_end_at = datetime.combine(week_end_date(week_start) + timedelta(days=1), time.min)
    return week_start_at, week_end_at


def slot_count(duration_minutes: int) -> int:
    """Round task duration up to the scheduler's slot granularity."""
    return max(1, ceil(duration_minutes / SLOT_MINUTES))


DEFAULT_WORKDAY_WINDOW = default_workday_window()
SLOTS_PER_DAY = DEFAULT_WORKDAY_WINDOW.slots_per_day
TOTAL_WEEKLY_SLOTS = DEFAULT_WORKDAY_WINDOW.total_weekly_slots
