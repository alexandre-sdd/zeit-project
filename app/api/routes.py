from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.schemas import (
    BlockRead,
    DemoResetResponse,
    EventCreate,
    EventRead,
    HealthResponse,
    ScheduleGenerateRequest,
    ScheduleGenerateResponse,
    TaskCreate,
    TaskRead,
    UnscheduledTaskRead,
)
from app.db import models
from app.db.session import get_db
from app.core.settings import get_settings
from app.services.demo_service import DEMO_WEEK_START, ensure_demo_data, reset_demo_data
from app.services.planning_service import generate_schedule_for_user, list_blocks, list_events
from app.services.schedule_policy import week_end_date

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


def _block_to_read(block: models.Block) -> BlockRead:
    return BlockRead(
        id=block.id,
        user_id=block.user_id,
        task_id=block.task_id,
        event_id=block.event_id,
        task_title=block.task.title if block.task is not None else None,
        event_title=block.event.title if block.event is not None else None,
        starts_at=block.starts_at,
        ends_at=block.ends_at,
        location=block.location,
        status=block.status,
        lock_level=block.lock_level,
        generated_by=block.generated_by,
    )


def _unscheduled_to_read(title: str, user_id: int, est_duration_min: int, priority: int, reason: str, task_id: int | None = None, due_at=None) -> UnscheduledTaskRead:
    return UnscheduledTaskRead(
        task_id=task_id,
        user_id=user_id,
        title=title,
        est_duration_min=est_duration_min,
        priority=priority,
        due_at=due_at,
        reason=reason,
    )


@router.get("/", response_class=HTMLResponse)
def demo_page(request: Request, db: DbSession) -> HTMLResponse:
    """Render the recruiter-facing demo page."""
    state = ensure_demo_data(db)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_name": get_settings().app_name,
            "demo_user": state.user,
            "week_start": state.week_start,
            "week_end": week_end_date(state.week_start),
            "tasks": state.tasks,
            "events": state.events,
            "blocks": state.blocks,
            "task_count": len(state.tasks),
            "event_count": len(state.events),
            "block_count": len(state.blocks),
            "demo_week_start": DEMO_WEEK_START,
        },
    )


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
        due_at=payload.due_at,
        due_is_hard=payload.due_is_hard,
        priority=payload.priority,
        category=payload.category,
        preferred_location=payload.preferred_location,
        repeat_rule=payload.repeat_rule,
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


@router.get("/events", response_model=list[EventRead])
def get_events(db: DbSession, user_id: int | None = None) -> list[EventRead]:
    """List events, optionally scoped to a specific user."""
    return list_events(db, user_id=user_id)


@router.post("/events", response_model=EventRead, status_code=status.HTTP_201_CREATED)
def create_event(payload: EventCreate, db: DbSession) -> EventRead:
    """Create a new hard event."""
    new_event = models.Event(
        user_id=payload.user_id,
        title=payload.title,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        location=payload.location,
        lock_level="hard",
        source=payload.source,
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return new_event


@router.get("/blocks", response_model=list[BlockRead])
def get_blocks(
    db: DbSession,
    user_id: int | None = None,
    week_start: date | None = None,
) -> list[BlockRead]:
    """List planned blocks, optionally filtered to a user and planning week."""
    return [_block_to_read(block) for block in list_blocks(db, user_id=user_id, week_start=week_start)]


@router.post("/schedule/generate", response_model=ScheduleGenerateResponse)
def generate_schedule(
    payload: ScheduleGenerateRequest,
    db: DbSession,
) -> ScheduleGenerateResponse:
    """Run the recruiter demo scheduler for a given user and week."""
    try:
        result = generate_schedule_for_user(
            db,
            user_id=payload.user_id,
            week_start=payload.week_start,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    unscheduled = [
        _unscheduled_to_read(
            task_id=item.task_id,
            user_id=item.user_id,
            title=item.title,
            est_duration_min=item.est_duration_min,
            priority=item.priority,
            due_at=item.due_at,
            reason=item.reason,
        )
        for item in result.unscheduled_tasks
    ]
    scheduled_blocks = [_block_to_read(block) for block in result.blocks]
    return ScheduleGenerateResponse(
        week_start=result.week_start,
        week_end=result.week_end,
        blocks=scheduled_blocks,
        unscheduled_tasks=unscheduled,
        scheduled_count=len(scheduled_blocks),
        unscheduled_count=len(unscheduled),
    )


@router.post("/demo/reset", response_model=DemoResetResponse)
def reset_demo(db: DbSession) -> DemoResetResponse:
    """Reset the deterministic demo data so each walkthrough starts clean."""
    state = reset_demo_data(db)
    return DemoResetResponse(
        user_id=state.user.id,
        week_start=state.week_start,
        task_count=len(state.tasks),
        event_count=len(state.events),
    )
