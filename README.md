# Zeit Project Skeleton

This repository provides a structured skeleton for the Zeit intelligent scheduling assistant project. The layout is organized to cleanly separate API, domain, persistence, solver, and service concerns.

```
zeit/
├── app/
│   ├── api/          # FastAPI routers
│   ├── core/         # settings, logging, timezone helpers
│   ├── db/           # ORM models, session management
│   ├── domain/       # pure domain entities (Task, Event, Block)
│   ├── solver/       # optimization entry points
│   ├── services/     # application services (planning, exports)
│   └── tests/        # pytest test suite
├── scripts/          # automation and utility scripts
├── README.md
└── requirements.txt
```

Key modules to explore first:

- `app/main.py` – FastAPI application entry point.
- `app/api/routes.py` – HTTP routes wired to services and persistence.
- `app/core/settings.py` – environment-driven configuration.
- `app/db/models.py` – relational schema for users, events, tasks, and blocks.
- `app/services/` – orchestration between domain entities, solver, and API.
- `app/solver/` – placeholder for the OR-Tools CP-SAT scheduling logic.

## Data Model

The initial relational schema is backed by SQLAlchemy models in `app/db/models.py`:

```sql
CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  email TEXT UNIQUE,
  timezone TEXT NOT NULL DEFAULT 'America/New_York'
);

CREATE TABLE events (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  title TEXT NOT NULL,
  starts_at TIMESTAMP NOT NULL,
  ends_at   TIMESTAMP NOT NULL,
  location  TEXT,
  lock_level TEXT NOT NULL DEFAULT 'hard',
  source TEXT NOT NULL DEFAULT 'manual'
);

CREATE TABLE tasks (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  title TEXT NOT NULL,
  est_duration_min INTEGER NOT NULL,
  due_at TIMESTAMP,
  due_is_hard BOOLEAN NOT NULL DEFAULT 0,
  priority INTEGER NOT NULL DEFAULT 0,
  category TEXT,
  preferred_location TEXT,
  repeat_rule TEXT
);

CREATE TABLE blocks (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  task_id INTEGER REFERENCES tasks(id),
  event_id INTEGER REFERENCES events(id),
  starts_at TIMESTAMP NOT NULL,
  ends_at   TIMESTAMP NOT NULL,
  location TEXT,
  status TEXT NOT NULL DEFAULT 'planned',
  lock_level TEXT NOT NULL DEFAULT 'none',
  generated_by TEXT NOT NULL DEFAULT 'solver'
);
```

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
