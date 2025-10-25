from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, init_db
from app.db import models

router = APIRouter()

# Initialize the DB (creates tables on startup)
init_db()

def get_db():
    """Provide a new SQLAlchemy session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/tasks")
def list_tasks(db: Session = Depends(get_db)):
    """List all tasks."""
    return db.query(models.Task).all()

@router.post("/tasks")
def create_task(
    title: str,
    est_duration_minutes: int,
    priority: int = 0,
    db: Session = Depends(get_db),
):
    """Create a new task."""
    new_task = models.Task(
        title=title,
        est_duration_minutes=est_duration_minutes,
        priority=priority,
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task
