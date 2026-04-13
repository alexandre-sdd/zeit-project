# Zeit

Zeit is an architecture-first prototype for an intelligent scheduling assistant. The repository is intentionally split into API, domain, persistence, service, and solver layers so the project is easy to reason about even though the scheduling engine is still at an early stage.

## Current Scope

- FastAPI application with a typed health endpoint and task CRUD foundation.
- SQLAlchemy data model for users, tasks, events, and generated schedule blocks.
- Service and solver seams in place for schedule generation and ICS export.
- Small pytest suite covering API smoke paths and calendar export behavior.

This is not yet a production scheduler. The value of the repo today is its structure, clarity, and extension points.

## Layout

```text
zeit_code/
├── app/
│   ├── api/          # FastAPI routes + request/response schemas
│   ├── core/         # settings, logging, timezone helpers
│   ├── db/           # ORM models and session management
│   ├── domain/       # pure dataclasses for scheduling concepts
│   ├── solver/       # optimization and heuristic entry points
│   ├── services/     # planning and calendar export orchestration
│   ├── tests/        # pytest suite
│   ├── db_visualizer.py
│   └── main.py
├── scripts/
├── README.md
└── requirements.txt
```

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
uvicorn app.main:app --reload
```

The app creates the SQLite schema on startup using the configured `ZEIT_DATABASE_URL`, which defaults to `sqlite:///./test.db`.

## API Example

```bash
curl http://127.0.0.1:8000/health

curl -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "title": "Prepare recruiter walkthrough",
    "est_duration_min": 45,
    "priority": 2
  }'

curl "http://127.0.0.1:8000/tasks?user_id=1"
```

## Data Model

Core entities live in [app/db/models.py](/Users/alexandresepulvedadedietrich/Code/Old_Projectx/Zeit/zeit_code/app/db/models.py) and mirror the planned scheduling workflow:

- `User` owns tasks, events, and blocks.
- `Task` captures work to be scheduled, including duration, priority, and optional due date.
- `Event` represents fixed calendar constraints.
- `Block` stores the generated schedule output.

## Optional Utility

To render the schema diagram, install `sqlalchemy-schemadisplay` and Graphviz, then run:

```bash
python app/db_visualizer.py
```

## Next Steps

See [RECRUITER_READINESS.md](/Users/alexandresepulvedadedietrich/Code/Old_Projectx/Zeit/zeit_code/RECRUITER_READINESS.md) for a concise review of what the repo already shows well, what still looks unfinished, and the highest-leverage improvements to make before sharing it more broadly.
