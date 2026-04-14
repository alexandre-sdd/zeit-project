"""
Pydantic schemas exposed by the HTTP API.
"""
from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.schedule_policy import SLOT_MINUTES, time_to_minutes


class HealthResponse(BaseModel):
    status: str = "ok"
    app_name: str
    environment: str


class TaskCreate(BaseModel):
    user_id: int = Field(..., gt=0)
    title: str = Field(..., min_length=1, max_length=255)
    est_duration_min: int = Field(..., gt=0)
    priority: int = Field(default=0, ge=0)
    due_at: datetime | None = None
    due_is_hard: bool = False
    category: str | None = Field(default=None, max_length=255)
    preferred_location: str | None = Field(default=None, max_length=255)
    repeat_rule: str | None = Field(default=None, max_length=255)


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    est_duration_min: int
    due_at: datetime | None = None
    due_is_hard: bool
    priority: int
    category: str | None = None
    preferred_location: str | None = None
    repeat_rule: str | None = None


class EventCreate(BaseModel):
    user_id: int = Field(..., gt=0)
    title: str = Field(..., min_length=1, max_length=255)
    starts_at: datetime
    ends_at: datetime
    location: str | None = Field(default=None, max_length=255)
    lock_level: str = "hard"
    source: str = "manual"

    @model_validator(mode="after")
    def validate_times(self) -> EventCreate:
        if self.ends_at <= self.starts_at:
            raise ValueError("`ends_at` must be later than `starts_at`")
        return self


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    starts_at: datetime
    ends_at: datetime
    location: str | None = None
    lock_level: str
    source: str


class BlockRead(BaseModel):
    id: int
    user_id: int
    task_id: int | None = None
    event_id: int | None = None
    task_title: str | None = None
    event_title: str | None = None
    task_priority: int | None = None
    task_category: str | None = None
    task_due_at: datetime | None = None
    starts_at: datetime
    ends_at: datetime
    duration_min: int
    location: str | None = None
    status: str
    lock_level: str
    generated_by: str


class UnscheduledTaskRead(BaseModel):
    task_id: int | None = None
    user_id: int
    title: str
    est_duration_min: int
    priority: int
    due_at: datetime | None = None
    reason: str


class SolverRunRead(BaseModel):
    engine: str
    ortools_available: bool
    status: str
    message: str
    objective_value: float | None = None
    diagnostics: dict[str, Any] | None = None


class ScheduleGenerateRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    week_start: date
    workday_start: time | None = None
    workday_end: time | None = None

    @model_validator(mode="after")
    def validate_workday_window(self) -> ScheduleGenerateRequest:
        if (self.workday_start is None) != (self.workday_end is None):
            raise ValueError("`workday_start` and `workday_end` must be provided together")
        if self.workday_start is None or self.workday_end is None:
            return self

        start_minutes = time_to_minutes(self.workday_start)
        end_minutes = time_to_minutes(self.workday_end)
        if start_minutes >= end_minutes:
            raise ValueError("`workday_start` must be earlier than `workday_end`")
        if start_minutes % SLOT_MINUTES != 0 or end_minutes % SLOT_MINUTES != 0:
            raise ValueError(f"Workday times must align to {SLOT_MINUTES}-minute increments")
        return self


class ScheduleGenerateResponse(BaseModel):
    week_start: date
    week_end: date
    blocks: list[BlockRead]
    unscheduled_tasks: list[UnscheduledTaskRead]
    solver_run: SolverRunRead
    scheduled_count: int
    unscheduled_count: int


class ScheduleRunRead(BaseModel):
    id: int
    user_id: int
    week_start: date
    created_at: datetime
    scheduled_count: int
    unscheduled_count: int
    constraints: dict[str, Any]
    tasks_to_plan: list[dict[str, Any]]
    planned_tasks: list[dict[str, Any]]
    unplanned_tasks: list[dict[str, Any]]
    solver: dict[str, Any]
    solution: dict[str, Any]


class DemoResetResponse(BaseModel):
    user_id: int
    week_start: date
    task_count: int
    event_count: int
