"""
SQLAlchemy models for the Zeit Project.

They define the core persistence layer for users, events, tasks, and the
resulting schedule blocks. The schema mirrors the initial ERD agreed on
for the project so other layers can rely on the same contract.
"""
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    timezone = Column(String, nullable=False, default="America/New_York")

    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="user", cascade="all, delete-orphan")
    blocks = relationship("Block", back_populates="user", cascade="all, delete-orphan")
    schedule_runs = relationship("ScheduleRun", back_populates="user", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    est_duration_min = Column(Integer, nullable=False)
    due_at = Column(DateTime, nullable=True)
    due_is_hard = Column(Boolean, nullable=False, default=False)
    priority = Column(Integer, nullable=False, default=0)
    category = Column(String, nullable=True)
    preferred_location = Column(String, nullable=True)
    repeat_rule = Column(String, nullable=True)
    user = relationship("User", back_populates="tasks")
    blocks = relationship("Block", back_populates="task")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    starts_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=False)
    location = Column(String, nullable=True)
    lock_level = Column(String, nullable=False, default="hard")  # hard|soft|ignore
    source = Column(String, nullable=False, default="manual")  # manual|calendar

    user = relationship("User", back_populates="events")
    blocks = relationship("Block", back_populates="event")


class Block(Base):
    __tablename__ = "blocks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    starts_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=False)
    location = Column(String, nullable=True)
    status = Column(String, nullable=False, default="planned")  # planned|done|skipped
    lock_level = Column(String, nullable=False, default="none")  # none|soft|hard
    generated_by = Column(String, nullable=False, default="solver")

    user = relationship("User", back_populates="blocks")
    task = relationship("Task", back_populates="blocks")
    event = relationship("Event", back_populates="blocks")

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "starts_at",
            "ends_at",
            name="uq_blocks_user_timespan",
        ),
    )


class ScheduleRun(Base):
    __tablename__ = "schedule_runs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    week_start = Column(Date, nullable=False)
    created_at = Column(DateTime, nullable=False)
    scheduled_count = Column(Integer, nullable=False, default=0)
    unscheduled_count = Column(Integer, nullable=False, default=0)
    constraints_json = Column(Text, nullable=False)
    tasks_to_plan_json = Column(Text, nullable=False)
    planned_tasks_json = Column(Text, nullable=False)
    unplanned_tasks_json = Column(Text, nullable=False)
    solver_json = Column(Text, nullable=False)
    solution_json = Column(Text, nullable=False)

    user = relationship("User", back_populates="schedule_runs")
