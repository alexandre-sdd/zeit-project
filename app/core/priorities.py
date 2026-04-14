"""
Shared priority-level definitions.

Zeit uses three priority levels across persistence, solver logic, API
payloads, diagnostics, exports, and the UI:
- urgent
- important
- when possible
"""
from __future__ import annotations

from typing import Final

PRIORITY_WHEN_POSSIBLE: Final[int] = 1
PRIORITY_IMPORTANT: Final[int] = 2
PRIORITY_URGENT: Final[int] = 3

MIN_PRIORITY: Final[int] = PRIORITY_WHEN_POSSIBLE
MAX_PRIORITY: Final[int] = PRIORITY_URGENT
DEFAULT_PRIORITY: Final[int] = PRIORITY_IMPORTANT

_PRIORITY_METADATA: Final[dict[int, dict[str, str]]] = {
    PRIORITY_URGENT: {
        "label": "Urgent",
        "short_label": "Urgent",
        "tiny_label": "Urg",
        "css_class": "urgent",
    },
    PRIORITY_IMPORTANT: {
        "label": "Important",
        "short_label": "Important",
        "tiny_label": "Imp",
        "css_class": "important",
    },
    PRIORITY_WHEN_POSSIBLE: {
        "label": "When possible",
        "short_label": "When possible",
        "tiny_label": "WP",
        "css_class": "when-possible",
    },
}


def normalize_priority(priority: int | None) -> int:
    """Map legacy and nullable values onto the supported 3-level scale."""
    if priority is None:
        return DEFAULT_PRIORITY
    if priority > PRIORITY_URGENT:
        return PRIORITY_URGENT
    if priority < PRIORITY_WHEN_POSSIBLE:
        return PRIORITY_WHEN_POSSIBLE
    return priority


def priority_label(priority: int | None) -> str:
    return _PRIORITY_METADATA[normalize_priority(priority)]["label"]


def priority_short_label(priority: int | None) -> str:
    return _PRIORITY_METADATA[normalize_priority(priority)]["short_label"]


def priority_tiny_label(priority: int | None) -> str:
    return _PRIORITY_METADATA[normalize_priority(priority)]["tiny_label"]


def priority_css_class(priority: int | None) -> str:
    return _PRIORITY_METADATA[normalize_priority(priority)]["css_class"]


def priority_metadata() -> dict[int, dict[str, str | int]]:
    return {
        value: {
            "value": value,
            "label": data["label"],
            "short_label": data["short_label"],
            "tiny_label": data["tiny_label"],
            "css_class": data["css_class"],
        }
        for value, data in sorted(_PRIORITY_METADATA.items(), reverse=True)
    }


def priority_options() -> list[dict[str, str | int]]:
    return list(priority_metadata().values())
