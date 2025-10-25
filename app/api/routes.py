from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def read_root():
    """
    Root endpoint returning a welcome message. Extend this module with
    CRUD endpoints for tasks, events, and blocks as the project evolves.
    """
    return {"message": "Welcome to the Zeit Project API"}
