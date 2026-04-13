"""
Pydantic schemas exposed by the HTTP API.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    app_name: str
    environment: str


class TaskCreate(BaseModel):
    user_id: int = Field(..., gt=0)
    title: str = Field(..., min_length=1, max_length=255)
    est_duration_min: int = Field(..., gt=0)
    priority: int = Field(default=0, ge=0)


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
