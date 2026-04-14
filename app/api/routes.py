from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.schemas import (
    BlockRead,
    DemoResetResponse,
    EventCreate,
    EventRead,
    HealthResponse,
    ScheduleRunRead,
    ScheduleGenerateRequest,
    ScheduleGenerateResponse,
    SolverRunRead,
    TaskCreate,
    TaskRead,
    UnscheduledTaskRead,
)
from app.db import models
from app.db.session import get_db
from app.core.settings import get_settings
from app.services.demo_service import DEMO_WEEK_START, ensure_demo_data, reset_demo_data
from app.services.calendar_export import schedule_to_ics
from app.services.planning_service import (
    generate_schedule_for_user,
    list_blocks,
    list_events,
    list_schedule_runs,
    load_schedule_run_payload,
)
from app.services.schedule_policy import (
    SLOT_MINUTES,
    default_workday_window,
    minutes_to_time_value,
    week_bounds,
    week_end_date,
    workday_time_labels,
)
from app.solver.cp_sat_model import get_solver_runtime_status

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


def _task_to_read(task: models.Task) -> TaskRead:
    return TaskRead.model_validate(task)


def _event_to_read(event: models.Event) -> EventRead:
    return EventRead.model_validate(event)


def _block_to_read(block: models.Block) -> BlockRead:
    duration_min = int((block.ends_at - block.starts_at).total_seconds() // 60)
    return BlockRead(
        id=block.id,
        user_id=block.user_id,
        task_id=block.task_id,
        event_id=block.event_id,
        task_title=block.task.title if block.task is not None else None,
        event_title=block.event.title if block.event is not None else None,
        task_priority=block.task.priority if block.task is not None else None,
        task_category=block.task.category if block.task is not None else None,
        task_due_at=block.task.due_at if block.task is not None else None,
        starts_at=block.starts_at,
        ends_at=block.ends_at,
        duration_min=duration_min,
        location=block.location,
        status=block.status,
        lock_level=block.lock_level,
        generated_by=block.generated_by,
    )


def _solver_run_to_read(solver_run) -> SolverRunRead:
    return SolverRunRead(
        engine=solver_run.engine,
        ortools_available=solver_run.ortools_available,
        status=solver_run.status,
        message=solver_run.message,
        objective_value=solver_run.objective_value,
    )


def _schedule_run_to_read(schedule_run: models.ScheduleRun) -> ScheduleRunRead:
    payload = load_schedule_run_payload(schedule_run)
    return ScheduleRunRead(
        id=schedule_run.id,
        user_id=schedule_run.user_id,
        week_start=schedule_run.week_start,
        created_at=schedule_run.created_at,
        scheduled_count=schedule_run.scheduled_count,
        unscheduled_count=schedule_run.unscheduled_count,
        constraints=payload["constraints"],
        tasks_to_plan=payload["tasks_to_plan"],
        planned_tasks=payload["planned_tasks"],
        unplanned_tasks=payload["unplanned_tasks"],
        solver=payload["solver"],
        solution=payload["solution"],
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
    """Render the visitor-facing demo page."""
    state = ensure_demo_data(db)
    workday_window = default_workday_window()
    task_payload = [_task_to_read(task).model_dump(mode="json") for task in state.tasks]
    event_payload = [_event_to_read(event).model_dump(mode="json") for event in state.events]
    block_payload = [_block_to_read(block).model_dump(mode="json") for block in state.blocks]
    run_log_payload = [
        _schedule_run_to_read(schedule_run).model_dump(mode="json")
        for schedule_run in list_schedule_runs(db, user_id=state.user.id, week_start=state.week_start, limit=5)
    ]
    weekdays = [
        {
            "label": (state.week_start + timedelta(days=day_index)).strftime("%a"),
            "date_label": (state.week_start + timedelta(days=day_index)).strftime("%b %d"),
        }
        for day_index in range(5)
    ]
    time_labels = workday_time_labels(workday_window)
    runtime = get_solver_runtime_status()
    initial_solver_run = SolverRunRead(
        engine=runtime.engine,
        ortools_available=runtime.ortools_available,
        status="IDLE",
        message=(
            f"{runtime.message} "
            + (
                f"The page currently shows {len(state.blocks)} persisted planned blocks."
                if state.blocks
                else "Run Generate Schedule to record a fresh optimisation result."
            )
        ),
        objective_value=None,
    )
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
            "initial_tasks": task_payload,
            "initial_events": event_payload,
            "initial_blocks": block_payload,
            "weekdays": weekdays,
            "time_labels": time_labels,
            "workday_start_value": minutes_to_time_value(workday_window.start_minutes),
            "workday_end_value": minutes_to_time_value(workday_window.end_minutes),
            "workday_slot_count": workday_window.slots_per_day,
            "slot_minutes": SLOT_MINUTES,
            "initial_solver_run": initial_solver_run.model_dump(mode="json"),
            "initial_schedule_runs": run_log_payload,
            "assets": {
                "demo_css": str(request.app.url_path_for("static", path="demo.css")),
                "favicon": str(request.app.url_path_for("static", path="favicon.svg")),
            },
            "routes": {
                "create_task": str(request.app.url_path_for("create_task")),
                "create_event": str(request.app.url_path_for("create_event")),
                "reset_demo": str(request.app.url_path_for("reset_demo")),
                "generate_schedule": str(request.app.url_path_for("generate_schedule")),
                "list_schedule_runs": str(request.app.url_path_for("list_schedule_runs_route")),
                "export_calendar_ics": str(request.app.url_path_for("export_calendar_ics")),
                "delete_task_template": str(request.app.url_path_for("delete_task", task_id=0)),
                "delete_event_template": str(request.app.url_path_for("delete_event", event_id=0)),
            },
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
    return [_task_to_read(task) for task in query.order_by(models.Task.id.asc()).all()]


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


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: DbSession) -> Response:
    """Delete a task and any scheduled blocks linked to it."""
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} was not found")

    db.query(models.Block).filter(models.Block.task_id == task_id).delete(synchronize_session=False)
    db.delete(task)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/events", response_model=list[EventRead])
def get_events(db: DbSession, user_id: int | None = None) -> list[EventRead]:
    """List events, optionally scoped to a specific user."""
    return [_event_to_read(event) for event in list_events(db, user_id=user_id)]


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


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(event_id: int, db: DbSession) -> Response:
    """Delete a fixed calendar event and any linked blocks."""
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Event {event_id} was not found")

    db.query(models.Block).filter(models.Block.event_id == event_id).delete(synchronize_session=False)
    db.delete(event)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/blocks", response_model=list[BlockRead])
def get_blocks(
    db: DbSession,
    user_id: int | None = None,
    week_start: date | None = None,
) -> list[BlockRead]:
    """List planned blocks, optionally filtered to a user and planning week."""
    return [_block_to_read(block) for block in list_blocks(db, user_id=user_id, week_start=week_start)]


@router.get("/calendar/export.ics")
def export_calendar_ics(
    db: DbSession,
    user_id: int,
    week_start: date,
) -> Response:
    """Download the visible planning week as an ICS calendar file."""
    blocks = list_blocks(db, user_id=user_id, week_start=week_start)
    start_dt, end_dt = week_bounds(week_start)
    events = [
        event
        for event in list_events(db, user_id=user_id)
        if event.starts_at < end_dt and event.ends_at > start_dt
    ]
    ics_payload = schedule_to_ics(blocks=blocks, events=events)
    filename = f"zeit_calendar_{week_start.isoformat()}.ics"
    return Response(
        content=ics_payload,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/schedule/generate", response_model=ScheduleGenerateResponse)
def generate_schedule(
    payload: ScheduleGenerateRequest,
    db: DbSession,
) -> ScheduleGenerateResponse:
    """Run the visitor demo scheduler for a given user and week."""
    try:
        result = generate_schedule_for_user(
            db,
            user_id=payload.user_id,
            week_start=payload.week_start,
            workday_start=payload.workday_start,
            workday_end=payload.workday_end,
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
        solver_run=_solver_run_to_read(result.solver_run),
        scheduled_count=len(scheduled_blocks),
        unscheduled_count=len(unscheduled),
    )


@router.get("/schedule/runs", response_model=list[ScheduleRunRead], name="list_schedule_runs_route")
def get_schedule_runs(
    db: DbSession,
    user_id: int,
    week_start: date | None = None,
    limit: int = 10,
) -> list[ScheduleRunRead]:
    """List recent schedule generation logs for a user and optional week."""
    safe_limit = min(max(limit, 1), 20)
    schedule_runs = list_schedule_runs(db, user_id=user_id, week_start=week_start, limit=safe_limit)
    return [_schedule_run_to_read(schedule_run) for schedule_run in schedule_runs]


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
