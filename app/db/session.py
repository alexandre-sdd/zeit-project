"""
Database session management. Initializes an SQLite database by default,
which can be replaced by PostgreSQL in production.
"""
from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .base import Base
from . import models as _models  # noqa: F401  # Ensure metadata is registered before migrations run.
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


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _alembic_config() -> Config:
    config = Config(str(_project_root() / "alembic.ini"))
    config.set_main_option("script_location", str(_project_root() / "alembic"))
    config.set_main_option("sqlalchemy.url", engine.url.render_as_string(hide_password=False).replace("%", "%%"))
    return config


def _schema_matches_metadata() -> bool:
    inspector = inspect(engine)
    expected_tables = Base.metadata.tables
    existing_tables = set(inspector.get_table_names())
    if not expected_tables.keys() <= existing_tables:
        return False

    for table_name, table in expected_tables.items():
        existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
        expected_columns = set(table.columns.keys())
        if not expected_columns.issubset(existing_columns):
            return False
    return True


def _stamp_head() -> None:
    config = _alembic_config()
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.stamp(config, "head")


def _upgrade_head() -> None:
    config = _alembic_config()
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


def init_db() -> None:
    """Apply Alembic migrations and fail loudly on stale unmanaged schemas."""
    inspector = inspect(engine)
    has_alembic_version = inspector.has_table("alembic_version")

    if not has_alembic_version:
        existing_tables = set(inspector.get_table_names())
        tracked_tables = set(Base.metadata.tables.keys())
        has_tracked_schema = bool(existing_tables & tracked_tables)

        if has_tracked_schema:
            if _schema_matches_metadata():
                _stamp_head()
            else:
                if engine.url.get_backend_name() == "sqlite":
                    raise RuntimeError(
                        "Existing SQLite schema predates Alembic migrations and no longer matches the app "
                        "metadata. Back up and remove the local database file, or migrate it manually."
                    )
                raise RuntimeError(
                    "Existing database schema is not managed by Alembic and does not match the current metadata."
                )

    _upgrade_head()
