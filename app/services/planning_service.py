"""
Planning service orchestrating the end-to-end scheduling workflow.

It bridges persistence, domain entities, and the solver to offer a
clean API to higher layers such as HTTP routes or CLI commands.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, time
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.db import models
from app.domain.entities import Block, Event, ScheduleResult, SolverRun, Task, UnscheduledTask
from app.services.schedule_policy import week_bounds, week_end_date
from app.solver.cp_sat_model import build_schedule


@dataclass(slots=True)
class PlanningRunResult:
    week_start: date
    week_end: date
    blocks: list[models.Block]
    unscheduled_tasks: list[UnscheduledTask]
    solver_run: SolverRun


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

    db.commit()
    persisted_blocks = list_blocks(db, user_id=user_id, week_start=week_start)
    return PlanningRunResult(
        week_start=week_start,
        week_end=week_end_date(week_start),
        blocks=persisted_blocks,
        unscheduled_tasks=schedule_result.unscheduled_tasks,
        solver_run=schedule_result.solver_run,
    )
