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
def list_tasks(user_id: int | None = None, db: Session = Depends(get_db)):
    """List tasks, optionally scoped to a specific user."""
    query = db.query(models.Task)
    if user_id is not None:
        query = query.filter(models.Task.user_id == user_id)
    return query.all()

@router.post("/tasks")
def create_task(
    user_id: int,
    title: str,
    est_duration_min: int,
    priority: int = 0,
    db: Session = Depends(get_db),
):
    """Create a new task."""
    new_task = models.Task(
        user_id=user_id,
        title=title,
        est_duration_min=est_duration_min,
        priority=priority,
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task
