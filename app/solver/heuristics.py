"""
Heuristic helpers complementing the core CP-SAT model.

These functions can be used for warm-starting the solver, providing
fallback plans, or generating insights such as priority scores.
"""
from __future__ import annotations

from collections.abc import Iterable
from datetime import timedelta

from app.domain.entities import Task


def estimate_daily_capacity(tasks: Iterable[Task]) -> timedelta:
    """Rudimentary capacity estimator based on total task duration."""
    total_minutes = sum(task.est_duration_min for task in tasks)
    return timedelta(minutes=total_minutes)
