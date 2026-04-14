"""
Planning service orchestrating the end-to-end scheduling workflow.

It bridges persistence, domain entities, and the solver to offer a
clean API to higher layers such as HTTP routes or CLI commands.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
import json
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.db import models
from app.domain.entities import Block, Event, ScheduleResult, SolverRun, Task, UnscheduledTask
from app.services.schedule_policy import SLOT_MINUTES, resolve_workday_window, week_bounds, week_end_date
from app.solver.cp_sat_model import build_schedule


@dataclass(slots=True)
class PlanningRunResult:
    week_start: date
    week_end: date
    blocks: list[models.Block]
    unscheduled_tasks: list[UnscheduledTask]
    solver_run: SolverRun
    schedule_run: models.ScheduleRun


def _to_domain_task(task: models.Task) -> Task:
    return Task(
        id=task.id,
        user_id=task.user_id,
        title=task.title,
        est_duration_min=task.est_duration_min,
        due_at=task.due_at,
        due_is_hard=task.due_is_hard,
        priority=task.priority,
        category=task.category,
        preferred_location=task.preferred_location,
        repeat_rule=task.repeat_rule,
    )


def _to_domain_event(event: models.Event) -> Event:
    return Event(
        id=event.id,
        user_id=event.user_id,
        title=event.title,
        starts_at=event.starts_at,
        ends_at=event.ends_at,
        location=event.location,
        lock_level=event.lock_level,
        source=event.source,
    )


def list_events(db: Session, *, user_id: int | None = None) -> list[models.Event]:
    query = db.query(models.Event)
    if user_id is not None:
        query = query.filter(models.Event.user_id == user_id)
    return query.order_by(models.Event.starts_at.asc(), models.Event.id.asc()).all()


def list_blocks(
    db: Session,
    *,
    user_id: int | None = None,
    week_start: date | None = None,
) -> list[models.Block]:
    query = db.query(models.Block).options(joinedload(models.Block.task), joinedload(models.Block.event))
    if user_id is not None:
        query = query.filter(models.Block.user_id == user_id)
    if week_start is not None:
        start_dt, end_dt = week_bounds(week_start)
        query = query.filter(models.Block.starts_at >= start_dt, models.Block.starts_at < end_dt)
    return query.order_by(models.Block.starts_at.asc(), models.Block.id.asc()).all()


def list_schedule_runs(
    db: Session,
    *,
    user_id: int | None = None,
    week_start: date | None = None,
    limit: int = 10,
) -> list[models.ScheduleRun]:
    query = db.query(models.ScheduleRun)
    if user_id is not None:
        query = query.filter(models.ScheduleRun.user_id == user_id)
    if week_start is not None:
        query = query.filter(models.ScheduleRun.week_start == week_start)
    return query.order_by(models.ScheduleRun.created_at.desc(), models.ScheduleRun.id.desc()).limit(limit).all()


def load_schedule_run_payload(schedule_run: models.ScheduleRun) -> dict[str, Any]:
    return {
        "constraints": json.loads(schedule_run.constraints_json),
        "tasks_to_plan": json.loads(schedule_run.tasks_to_plan_json),
        "planned_tasks": json.loads(schedule_run.planned_tasks_json),
        "unplanned_tasks": json.loads(schedule_run.unplanned_tasks_json),
        "solver": json.loads(schedule_run.solver_json),
        "solution": json.loads(schedule_run.solution_json),
    }


def plan_schedule(
    tasks: Iterable[Task],
    events: Iterable[Event],
    *,
    week_start: date,
    options: dict[str, Any] | None = None,
) -> ScheduleResult:
    """Generate a schedule using the solver."""
    solver_options = dict(options or {})
    solver_options["week_start"] = week_start
    return build_schedule(tasks, events, options=solver_options)


def _json_default(value: Any) -> str:
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _json_dump(value: Any) -> str:
    return json.dumps(value, default=_json_default)


def _serialize_task_row(task: models.Task) -> dict[str, Any]:
    return {
        "task_id": task.id,
        "title": task.title,
        "est_duration_min": task.est_duration_min,
        "priority": task.priority,
        "due_at": task.due_at,
        "due_is_hard": task.due_is_hard,
        "category": task.category,
        "preferred_location": task.preferred_location,
        "repeat_rule": task.repeat_rule,
    }


def _serialize_event_row(event: models.Event) -> dict[str, Any]:
    return {
        "event_id": event.id,
        "title": event.title,
        "starts_at": event.starts_at,
        "ends_at": event.ends_at,
        "location": event.location,
        "lock_level": event.lock_level,
        "source": event.source,
    }


def _serialize_unscheduled_task(task: UnscheduledTask) -> dict[str, Any]:
    return {
        "task_id": task.task_id,
        "title": task.title,
        "est_duration_min": task.est_duration_min,
        "priority": task.priority,
        "due_at": task.due_at,
        "reason": task.reason,
    }


def _serialize_solver_run(solver_run: SolverRun) -> dict[str, Any]:
    return {
        "engine": solver_run.engine,
        "ortools_available": solver_run.ortools_available,
        "status": solver_run.status,
        "message": solver_run.message,
        "objective_value": solver_run.objective_value,
    }


def _serialize_planned_block(block: Block, task_lookup: dict[int, models.Task]) -> dict[str, Any]:
    task = task_lookup.get(block.task_id) if block.task_id is not None else None
    duration_min = int((block.ends_at - block.starts_at).total_seconds() // 60)
    return {
        "task_id": block.task_id,
        "title": task.title if task is not None else None,
        "starts_at": block.starts_at,
        "ends_at": block.ends_at,
        "duration_min": duration_min,
        "priority": task.priority if task is not None else None,
        "due_at": task.due_at if task is not None else None,
        "category": task.category if task is not None else None,
        "location": block.location,
    }


def _create_schedule_run(
    *,
    user_id: int,
    week_start: date,
    task_rows: list[models.Task],
    event_rows: list[models.Event],
    schedule_result: ScheduleResult,
    workday_start: time | None,
    workday_end: time | None,
) -> models.ScheduleRun:
    workday_window = resolve_workday_window(workday_start=workday_start, workday_end=workday_end)
    task_lookup = {task.id: task for task in task_rows if task.id is not None}
    planned_tasks = [
        _serialize_planned_block(block, task_lookup)
        for block in sorted(schedule_result.blocks, key=lambda item: item.starts_at)
    ]
    unplanned_tasks = [_serialize_unscheduled_task(task) for task in schedule_result.unscheduled_tasks]
    constraints = {
        "week_start": week_start,
        "week_end": week_end_date(week_start),
        "workday_start": workday_window.start_time,
        "workday_end": workday_window.end_time,
        "slot_minutes": SLOT_MINUTES,
        "events": [_serialize_event_row(event) for event in event_rows],
    }
    tasks_to_plan = [_serialize_task_row(task) for task in task_rows]
    solver_payload = _serialize_solver_run(schedule_result.solver_run)
    solution = {
        "scheduled_count": len(planned_tasks),
        "unscheduled_count": len(unplanned_tasks),
        "blocks": planned_tasks,
        "unscheduled_tasks": unplanned_tasks,
    }
    return models.ScheduleRun(
        user_id=user_id,
        week_start=week_start,
        created_at=datetime.now(UTC),
        scheduled_count=len(planned_tasks),
        unscheduled_count=len(unplanned_tasks),
        constraints_json=_json_dump(constraints),
        tasks_to_plan_json=_json_dump(tasks_to_plan),
        planned_tasks_json=_json_dump(planned_tasks),
        unplanned_tasks_json=_json_dump(unplanned_tasks),
        solver_json=_json_dump(solver_payload),
        solution_json=_json_dump(solution),
    )


def generate_schedule_for_user(
    db: Session,
    *,
    user_id: int,
    week_start: date,
    workday_start: time | None = None,
    workday_end: time | None = None,
) -> PlanningRunResult:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise LookupError(f"User {user_id} was not found")

    task_rows = (
        db.query(models.Task)
        .filter(models.Task.user_id == user_id)
        .order_by(models.Task.priority.desc(), models.Task.id.asc())
        .all()
    )
    event_rows = list_events(db, user_id=user_id)

    schedule_result = plan_schedule(
        [_to_domain_task(task) for task in task_rows],
        [_to_domain_event(event) for event in event_rows],
        week_start=week_start,
        options={
            "workday_start": workday_start,
            "workday_end": workday_end,
        },
    )

    start_dt, end_dt = week_bounds(week_start)
    db.query(models.Block).filter(
        models.Block.user_id == user_id,
        models.Block.generated_by == "solver",
        models.Block.starts_at >= start_dt,
        models.Block.starts_at < end_dt,
    ).delete(synchronize_session=False)
    db.flush()

    for block in schedule_result.blocks:
        db.add(
            models.Block(
                user_id=block.user_id,
                task_id=block.task_id,
                event_id=block.event_id,
                starts_at=block.starts_at,
                ends_at=block.ends_at,
                location=block.location,
                status=block.status,
                lock_level=block.lock_level,
                generated_by=block.generated_by,
            )
        )

    schedule_run = _create_schedule_run(
        user_id=user_id,
        week_start=week_start,
        task_rows=task_rows,
        event_rows=event_rows,
        schedule_result=schedule_result,
        workday_start=workday_start,
        workday_end=workday_end,
    )
    db.add(schedule_run)
    db.commit()
    db.refresh(schedule_run)
    persisted_blocks = list_blocks(db, user_id=user_id, week_start=week_start)
    return PlanningRunResult(
        week_start=week_start,
        week_end=week_end_date(week_start),
        blocks=persisted_blocks,
        unscheduled_tasks=schedule_result.unscheduled_tasks,
        solver_run=schedule_result.solver_run,
        schedule_run=schedule_run,
    )
