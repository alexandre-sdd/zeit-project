"""
Calendar export service.

Converts planned blocks into ICS calendar entries so users can ingest
the resulting schedule into their calendar providers.
"""
from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from app.domain.entities import Block


def _as_utc(dt: datetime) -> datetime:
    """Normalize datetimes so ICS export is consistent across environments."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _escape_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def _append_ics_event(
    lines: list[str],
    *,
    uid: str,
    dtstamp: str,
    starts_at: datetime,
    ends_at: datetime,
    summary: str,
    description: str | None = None,
    location: str | None = None,
) -> None:
    lines.extend(
        [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{dtstamp}",
            f"DTSTART:{starts_at.strftime('%Y%m%dT%H%M%SZ')}",
            f"DTEND:{ends_at.strftime('%Y%m%dT%H%M%SZ')}",
            f"SUMMARY:{_escape_text(summary)}",
        ]
    )
    if description:
        lines.append(f"DESCRIPTION:{_escape_text(description)}")
    if location:
        lines.append(f"LOCATION:{_escape_text(location)}")
    lines.append("END:VEVENT")


def blocks_to_ics(blocks: Iterable[Block]) -> str:
    """
    Serialize blocks into a minimal ICS string.

    The implementation is intentionally lightweight and focuses on
    providing a clear seam for a richer export in the future.
    """
    now = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:-//Zeit//Scheduler//EN"]
    for block in blocks:
        starts_at = _as_utc(block.starts_at)
        ends_at = _as_utc(block.ends_at)
        _append_ics_event(
            lines,
            uid=f"block-{block.id or 'generated'}-{starts_at.strftime('%Y%m%dT%H%M%SZ')}@zeit",
            dtstamp=now,
            starts_at=starts_at,
            ends_at=ends_at,
            summary=f"{block.generated_by.title()} Block",
        )
    lines.append("END:VCALENDAR")
    return "\n".join(lines)


def schedule_to_ics(*, blocks: Iterable[object], events: Iterable[object]) -> str:
    """Serialize the visible calendar week, including fixed events and planned blocks."""
    now = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Zeit//Scheduler//EN"]

    for event in events:
        starts_at = _as_utc(getattr(event, "starts_at"))
        ends_at = _as_utc(getattr(event, "ends_at"))
        _append_ics_event(
            lines,
            uid=f"event-{getattr(event, 'id', 'generated')}-{starts_at.strftime('%Y%m%dT%H%M%SZ')}@zeit",
            dtstamp=now,
            starts_at=starts_at,
            ends_at=ends_at,
            summary=str(getattr(event, "title", "Fixed Event")),
            description="Fixed calendar constraint",
            location=getattr(event, "location", None),
        )

    for block in blocks:
        starts_at = _as_utc(getattr(block, "starts_at"))
        ends_at = _as_utc(getattr(block, "ends_at"))
        task = getattr(block, "task", None)
        task_title = getattr(task, "title", None)
        priority = getattr(task, "priority", None)
        description_parts = ["Generated task block"]
        if priority is not None:
            description_parts.append(f"Priority P{priority}")
        if getattr(block, "generated_by", None):
            description_parts.append(f"Engine: {getattr(block, 'generated_by')}")
        _append_ics_event(
            lines,
            uid=f"task-block-{getattr(block, 'id', 'generated')}-{starts_at.strftime('%Y%m%dT%H%M%SZ')}@zeit",
            dtstamp=now,
            starts_at=starts_at,
            ends_at=ends_at,
            summary=str(task_title or "Planned Task Block"),
            description=" | ".join(description_parts),
            location=getattr(block, "location", None),
        )

    lines.append("END:VCALENDAR")
    return "\n".join(lines)
