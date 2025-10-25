"""
SQLAlchemy models for the Zeit Project. These models define the tables
used for tasks, events, and blocks. Additional fields and
relationships can be added as the project requirements evolve.
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    est_duration_minutes = Column(Integer, nullable=False)
    due_at = Column(DateTime, nullable=True)
    due_is_hard = Column(Boolean, default=False)
    priority = Column(Integer, default=0)
    category = Column(String, nullable=True)
    preferred_location = Column(String, nullable=True)

    blocks = relationship("Block", back_populates="task")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    starts_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=False)
    location = Column(String, nullable=True)
    lock_level = Column(String, default="hard")  # 'hard' | 'soft' | 'ignore'
    source = Column(String, default="manual")

    blocks = relationship("Block", back_populates="event")


class Block(Base):
    __tablename__ = "blocks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    starts_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=False)
    location = Column(String, nullable=True)
    status = Column(String, default="planned")  # planned|done|skipped
    lock_level = Column(String, default="none")  # none|soft|hard
    generated_by = Column(String, default="solver")

    task = relationship("Task", back_populates="blocks")
    event = relationship("Event", back_populates="blocks")
