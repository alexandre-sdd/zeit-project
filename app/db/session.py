"""
Database session management. Initializes an SQLite database by default,
which can be replaced by PostgreSQL in production.
"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .base import Base
from app.core.settings import get_settings


def _create_engine() -> Engine:
    """Build the SQLAlchemy engine from environment-backed settings."""
    database_url = get_settings().database_url
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args)


engine = _create_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Provide a database session scoped to a single request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create the database schema if it does not already exist."""
    Base.metadata.create_all(bind=engine)
