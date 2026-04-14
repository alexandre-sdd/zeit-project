"""
Base declarative class for SQLAlchemy models.

Schema creation and evolution are handled through Alembic migrations;
`Base.metadata` is exposed so both the ORM and Alembic can target the
same model registry.
"""
from sqlalchemy.orm import declarative_base

Base = declarative_base()
