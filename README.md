# Zeit Project Skeleton

This repository provides a skeleton for the Zeit intelligent scheduling assistant project. It includes:

- `app/main.py` – entry point for the FastAPI application.
- `app/db/models.py` – SQLAlchemy models for tasks, events and blocks.
- `app/db/base.py` – Declarative base and model imports.
- `app/db/session.py` – Session management.
- `app/api/routes.py` – Placeholder for API routes.
- `requirements.txt` – Python dependencies.

## Getting Started

1. **Create a virtual environment and install dependencies**:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Initialize the database**:

   Run the following in a Python shell or script to create the tables:

   ```python
   from app.db.session import init_db
   init_db()
   ```

3. **Run the FastAPI server**:

   ```bash
   uvicorn app.main:app --reload
   ```

This skeleton provides a starting point; you can extend it with CRUD endpoints, scheduling logic using OR-Tools, and additional services as described in the project plan.
