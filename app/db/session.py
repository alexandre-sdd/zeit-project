"""
Database session management. Initializes an SQLite database by default,
which can be replaced by PostgreSQL in production.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .base import Base

# SQLite database URL for development. Replace with PostgreSQL in production.
DATABASE_URL = "sqlite:///./test.db"

# Create engine and sessionmaker
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite-specific argument
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """
    Create all tables in the database. Call this at startup to ensure
the database schema exists.
    """
    Base.metadata.create_all(bind=engine)
