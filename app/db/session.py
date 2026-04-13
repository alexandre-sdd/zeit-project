"""
Database session management. Initializes an SQLite database by default,
which can be replaced by PostgreSQL in production.
"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, inspect
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
    """Create the database schema and refresh stale local SQLite schemas if needed."""
    if engine.url.get_backend_name() == "sqlite":
        Base.metadata.create_all(bind=engine)
        inspector = inspect(engine)
        for table_name, table in Base.metadata.tables.items():
            if not inspector.has_table(table_name):
                continue
            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            expected_columns = set(table.columns.keys())
            if expected_columns.issubset(existing_columns):
                continue

            # The local demo DB predates the current schema. Rebuild it so the app boots cleanly.
            Base.metadata.drop_all(bind=engine)
            Base.metadata.create_all(bind=engine)
            return

    Base.metadata.create_all(bind=engine)
