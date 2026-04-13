from __future__ import annotations

from datetime import datetime

from app.domain.entities import Block
from app.services.calendar_export import blocks_to_ics


def test_blocks_to_ics_emits_calendar_entries() -> None:
    ics_payload = blocks_to_ics(
        [
            Block(
                id=1,
                user_id=1,
                task_id=1,
                event_id=None,
                starts_at=datetime(2026, 1, 2, 9, 0, 0),
                ends_at=datetime(2026, 1, 2, 9, 45, 0),
                generated_by="solver",
            )
        ]
    )

    assert "BEGIN:VCALENDAR" in ics_payload
    assert "BEGIN:VEVENT" in ics_payload
    assert "DTSTART:20260102T090000Z" in ics_payload
    assert "DTEND:20260102T094500Z" in ics_payload
    assert "SUMMARY:Solver Block" in ics_payload
