"""
Pydantic schemas exposed by the HTTP API.
"""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class ScheduleGenerateRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    week_start: date


class ScheduleGenerateResponse(BaseModel):
    week_start: date
    week_end: date
    blocks: list[BlockRead]
    unscheduled_tasks: list[UnscheduledTaskRead]
    scheduled_count: int
    unscheduled_count: int


class DemoResetResponse(BaseModel):
    user_id: int
    week_start: date
    task_count: int
    event_count: int
