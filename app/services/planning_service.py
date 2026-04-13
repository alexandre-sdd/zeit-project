"""
Planning service orchestrating the end-to-end scheduling workflow.

It bridges persistence, domain entities, and the solver to offer a
clean API to higher layers such as HTTP routes or CLI commands.
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.domain.entities import Block, Event, Task
from app.solver.cp_sat_model import build_schedule


def plan_schedule(
    tasks: Iterable[Task],
    events: Iterable[Event],
    *,
    options: dict[str, Any] | None = None,
) -> list[Block]:
    """Generate a schedule using the solver."""
    return build_schedule(tasks, events, options=options)
