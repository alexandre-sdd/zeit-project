"""
Base declarative class for SQLAlchemy models. Import this and call
Base.metadata.create_all(bind=engine) to create tables.
"""
from sqlalchemy.orm import declarative_base

Base = declarative_base()
