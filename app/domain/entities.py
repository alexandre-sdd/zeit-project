"""
Domain entities for the Zeit project.

These dataclasses capture the shape of the core concepts independently
from persistence or transport layers. They can be used by services and
solver components without leaking ORM details.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(slots=True)
class User:
    id: Optional[int]
    email: str
    timezone: str = "America/New_York"


@dataclass(slots=True)
class Task:
    id: Optional[int]
    user_id: int
    title: str
    est_duration_min: int
    due_at: Optional[datetime] = None
    due_is_hard: bool = False
    priority: int = 0
    category: Optional[str] = None
    preferred_location: Optional[str] = None
    repeat_rule: Optional[str] = None


@dataclass(slots=True)
class Event:
    id: Optional[int]
    user_id: int
    title: str
    starts_at: datetime
    ends_at: datetime
    location: Optional[str] = None
    lock_level: str = "hard"  # hard | soft | ignore
    source: str = "manual"


@dataclass(slots=True)
class Block:
    id: Optional[int]
    user_id: int
    task_id: Optional[int]
    event_id: Optional[int]
    starts_at: datetime
    ends_at: datetime
    location: Optional[str] = None
    status: str = "planned"  # planned | done | skipped
    lock_level: str = "none"  # none | soft | hard
    generated_by: str = "solver"


@dataclass(slots=True)
class UnscheduledTask:
    task_id: Optional[int]
    user_id: int
    title: str
    est_duration_min: int
    priority: int = 0
    due_at: Optional[datetime] = None
    reason: str = "no_capacity"


@dataclass(slots=True)
class ScheduleResult:
    blocks: list[Block]
    unscheduled_tasks: list[UnscheduledTask]
