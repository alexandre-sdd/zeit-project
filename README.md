# Zeit

Zeit is a recruiter-friendly prototype for an intelligent scheduling assistant. It now includes a seeded demo week, a lightweight FastAPI UI, JSON endpoints for tasks/events/blocks, and a working scheduler that turns one workweek of constraints into a concrete plan.

## Current Scope

- FastAPI application with a server-rendered demo page at `/`.
- JSON endpoints for tasks, events, blocks, demo reset, and schedule generation.
- SQLAlchemy data model for users, tasks, events, and generated schedule blocks.
- A Monday-Friday, 9-5 scheduler that respects hard events and hard due dates, persists planned blocks, and reports unscheduled work.
- Automated tests covering solver behavior, API flows, and UI smoke paths.

This is still not a production scheduler. The value of the repo today is that the architecture is clear, the demo is runnable, and the core planning story is easy to explain in an interview.

## Layout

```text
zeit_code/
├── app/
│   ├── api/          # FastAPI routes + request/response schemas
│   ├── core/         # settings, logging, timezone helpers
│   ├── db/           # ORM models and session management
│   ├── domain/       # pure dataclasses for scheduling concepts
│   ├── solver/       # optimization and heuristic entry points
│   ├── services/     # planning, seeding, and calendar export orchestration
│   ├── static/       # recruiter demo styles
│   ├── templates/    # server-rendered demo UI
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

Then open `http://127.0.0.1:8000/` to see the seeded demo page. The app creates the SQLite schema on startup using the configured `ZEIT_DATABASE_URL`, which defaults to `sqlite:///./test.db`.

## Demo Flow

1. Open `/` and let the app seed the demo user if the database is empty.
2. Review or edit the seeded tasks and hard events.
3. Click `Generate Schedule` to create planned blocks for the week.
4. Review unscheduled tasks and reasons such as `no_capacity`, `hard_due_conflict`, or `outside_work_window`.
5. Use `Reset Seed Data` to return the demo to a deterministic baseline.

## API Examples

```bash
curl http://127.0.0.1:8000/health

curl -X POST http://127.0.0.1:8000/demo/reset \
  -H "Content-Type: application/json" \
  -d '{}'

curl -X POST http://127.0.0.1:8000/schedule/generate \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 2,
    "week_start": "2026-04-13"
  }'

curl "http://127.0.0.1:8000/blocks?user_id=2&week_start=2026-04-13"
```

## Data Model

Core entities live in [app/db/models.py](/Users/alexandresepulvedadedietrich/Code/Old_Projectx/Zeit/zeit_code/app/db/models.py) and mirror the planned scheduling workflow:

- `User` owns tasks, events, and blocks.
- `Task` captures work to be scheduled, including duration, priority, and optional due date.
- `Event` represents fixed calendar constraints.
- `Block` stores the generated schedule output.

## Scheduling Rules

- Planning window: Monday-Friday, `09:00` to `17:00`
- Scheduling granularity: 30-minute slots
- Tasks are kept as one contiguous block in v1
- Hard events block time completely
- Hard due tasks must finish before `due_at`
- If OR-Tools is not usable in the current runtime, the app falls back to a deterministic greedy scheduler so the demo still works

## Optional Utility

To render the schema diagram, install `sqlalchemy-schemadisplay` and Graphviz, then run:

```bash
python app/db_visualizer.py
```

## Validation

```bash
pytest -q
python -m compileall app
```

## Notes

See [RECRUITER_READINESS.md](/Users/alexandresepulvedadedietrich/Code/Old_Projectx/Zeit/zeit_code/RECRUITER_READINESS.md) for a concise review of what the repo now demonstrates well and what remains worth improving before a broader portfolio push.
