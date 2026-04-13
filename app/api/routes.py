from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db
from app.api.schemas import HealthResponse, TaskCreate, TaskRead
from app.core.settings import get_settings

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Simple health endpoint for local verification and smoke tests."""
    settings = get_settings()
    return HealthResponse(app_name=settings.app_name, environment=settings.environment)


@router.get("/tasks", response_model=list[TaskRead])
def list_tasks(db: DbSession, user_id: int | None = None):
    """List tasks, optionally scoped to a specific user."""
    query = db.query(models.Task)
    if user_id is not None:
        query = query.filter(models.Task.user_id == user_id)
    return query.order_by(models.Task.id.asc()).all()


@router.post("/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    db: DbSession,
) -> TaskRead:
    """Create a new task."""
    new_task = models.Task(
        user_id=payload.user_id,
        title=payload.title,
        est_duration_min=payload.est_duration_min,
        priority=payload.priority,
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task
