"""
Seed and load a deterministic demo week for the recruiter-facing flow.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session, joinedload

from app.db import models

from .schedule_policy import week_bounds

DEMO_USER_EMAIL = "demo@zeit.local"
DEMO_USER_TIMEZONE = "America/New_York"
DEMO_WEEK_START = date(2026, 4, 13)


@dataclass(slots=True)
class DemoState:
    user: models.User
    week_start: date
    tasks: list[models.Task]
    events: list[models.Event]
    blocks: list[models.Block]


def _dt(day_offset: int, hour: int, minute: int = 0) -> datetime:
    return datetime(
        year=DEMO_WEEK_START.year,
        month=DEMO_WEEK_START.month,
        day=DEMO_WEEK_START.day + day_offset,
        hour=hour,
        minute=minute,
    )


def get_or_create_demo_user(db: Session) -> models.User:
    user = db.query(models.User).filter(models.User.email == DEMO_USER_EMAIL).first()
    if user is not None:
        return user

    user = models.User(email=DEMO_USER_EMAIL, timezone=DEMO_USER_TIMEZONE)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def load_demo_state(db: Session, *, week_start: date = DEMO_WEEK_START) -> DemoState:
    user = get_or_create_demo_user(db)
    start_dt, end_dt = week_bounds(week_start)

    tasks = (
        db.query(models.Task)
        .filter(models.Task.user_id == user.id)
        .order_by(models.Task.priority.desc(), models.Task.id.asc())
        .all()
    )
    events = (
        db.query(models.Event)
        .filter(models.Event.user_id == user.id)
        .order_by(models.Event.starts_at.asc(), models.Event.id.asc())
        .all()
    )
    blocks = (
        db.query(models.Block)
        .options(joinedload(models.Block.task), joinedload(models.Block.event))
        .filter(
            models.Block.user_id == user.id,
            models.Block.starts_at >= start_dt,
            models.Block.starts_at < end_dt,
        )
        .order_by(models.Block.starts_at.asc(), models.Block.id.asc())
        .all()
    )
    return DemoState(user=user, week_start=week_start, tasks=tasks, events=events, blocks=blocks)


def ensure_demo_data(db: Session) -> DemoState:
    state = load_demo_state(db)
    if state.tasks and state.events:
        return state
    return reset_demo_data(db)


def reset_demo_data(db: Session) -> DemoState:
    user = get_or_create_demo_user(db)

    db.query(models.Block).filter(models.Block.user_id == user.id).delete(synchronize_session=False)
    db.query(models.Task).filter(models.Task.user_id == user.id).delete(synchronize_session=False)
    db.query(models.Event).filter(models.Event.user_id == user.id).delete(synchronize_session=False)
    db.flush()

    events = [
        models.Event(user_id=user.id, title="Weekly Standup", starts_at=_dt(0, 9, 30), ends_at=_dt(0, 10, 0), source="seed"),
        models.Event(user_id=user.id, title="Design Review", starts_at=_dt(0, 13, 0), ends_at=_dt(0, 14, 0), source="seed"),
        models.Event(user_id=user.id, title="User Interviews", starts_at=_dt(1, 11, 0), ends_at=_dt(1, 12, 30), source="seed"),
        models.Event(user_id=user.id, title="Mentor Session", starts_at=_dt(2, 10, 0), ends_at=_dt(2, 11, 0), source="seed"),
        models.Event(user_id=user.id, title="Sprint Planning", starts_at=_dt(2, 15, 0), ends_at=_dt(2, 16, 30), source="seed"),
        models.Event(user_id=user.id, title="Lunch and Learn", starts_at=_dt(3, 12, 0), ends_at=_dt(3, 13, 0), source="seed"),
        models.Event(user_id=user.id, title="Demo Rehearsal", starts_at=_dt(4, 10, 30), ends_at=_dt(4, 12, 0), source="seed"),
        models.Event(user_id=user.id, title="Weekly Recap", starts_at=_dt(4, 15, 0), ends_at=_dt(4, 16, 0), source="seed"),
    ]

    tasks = [
        models.Task(user_id=user.id, title="Build timeline demo", est_duration_min=180, priority=5, category="product"),
        models.Task(user_id=user.id, title="Fix CP-SAT edge cases", est_duration_min=240, priority=5, category="engineering"),
        models.Task(user_id=user.id, title="Prepare recruiter walkthrough", est_duration_min=90, priority=4, due_at=_dt(3, 15, 0), due_is_hard=True, category="presentation"),
        models.Task(user_id=user.id, title="Draft architecture notes", est_duration_min=150, priority=4, category="architecture"),
        models.Task(user_id=user.id, title="Candidate Q&A prep", est_duration_min=150, priority=3, category="presentation"),
        models.Task(user_id=user.id, title="Polish API docs", est_duration_min=120, priority=3, category="documentation"),
        models.Task(user_id=user.id, title="Performance cleanup", est_duration_min=180, priority=3, category="engineering"),
        models.Task(user_id=user.id, title="Visual polish pass", est_duration_min=180, priority=2, category="design"),
        models.Task(user_id=user.id, title="Record demo voiceover", est_duration_min=120, priority=2, due_at=_dt(4, 14, 0), due_is_hard=True, category="presentation"),
        models.Task(user_id=user.id, title="Write setup guide", est_duration_min=90, priority=2, category="documentation"),
        models.Task(user_id=user.id, title="Accessibility review", est_duration_min=180, priority=2, category="quality"),
        models.Task(user_id=user.id, title="Backlog grooming", est_duration_min=240, priority=1, category="planning"),
        models.Task(user_id=user.id, title="Impossible launch memo", est_duration_min=180, priority=5, due_at=_dt(0, 10, 0), due_is_hard=True, category="presentation"),
        models.Task(user_id=user.id, title="Oversized research block", est_duration_min=540, priority=1, category="research"),
    ]

    db.add_all(events)
    db.add_all(tasks)
    db.commit()
    return load_demo_state(db)
