"""
Calendar export service.

Converts planned blocks into ICS calendar entries so users can ingest
the resulting schedule into their calendar providers.
"""
from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from app.domain.entities import Block


def blocks_to_ics(blocks: Iterable[Block]) -> str:
    """
    Serialize blocks into a minimal ICS string.

    The implementation is intentionally lightweight and focuses on
    providing a clear seam for a richer export in the future.
    """
    now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:-//Zeit//Scheduler//EN"]
    for block in blocks:
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"DTSTAMP:{now}",
                f"DTSTART:{block.starts_at.strftime('%Y%m%dT%H%M%SZ')}",
                f"DTEND:{block.ends_at.strftime('%Y%m%dT%H%M%SZ')}",
                f"SUMMARY:{block.generated_by.title()} Block",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    return "\n".join(lines)
