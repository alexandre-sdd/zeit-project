# Zeit

Zeit is a User-friendly prototype for an intelligent scheduling assistant. It now includes a seeded demo week, a lightweight FastAPI UI, JSON endpoints for tasks/events/blocks, and a working scheduler that turns one workweek of constraints into a concrete plan.

## Current Scope

- FastAPI application with a server-rendered demo page at `/`.
- JSON endpoints for tasks, events, blocks, demo reset, and schedule generation.
- SQLAlchemy data model for users, tasks, events, and generated schedule blocks.
- A Monday-Friday, 9-5 scheduler that respects hard events and hard due dates, persists planned blocks, and reports unscheduled work.
- Automated tests covering solver behavior, API flows, and UI smoke paths.

This is still not a production scheduler. The value of the repo today is that the architecture is clear, the demo is runnable, and the core planning story is easy to explain in an interview.

## Layout

```text
zeit-project/
├── app/
│   ├── api/          # FastAPI routes + request/response schemas
│   ├── core/         # settings, logging, timezone helpers
│   ├── db/           # ORM models and session management
│   ├── domain/       # pure dataclasses for scheduling concepts
│   ├── solver/       # optimization and heuristic entry points
│   ├── services/     # planning, seeding, and calendar export orchestration
│   ├── static/       # User demo styles
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

## OR-Tools Runtime

The current default shell in this workspace is Python `3.13`, and the scheduler intentionally
falls back to the greedy planner there because the CP-SAT solve path is not stable in this runtime.
If you want to see real OR-Tools scheduling, run the app and tests in the existing `conda` env
named `zeit`, which uses Python `3.12`.

Examples:

```bash
conda run -n zeit uvicorn app.main:app --reload
conda run -n zeit pytest -q
```

Or use the project wrapper:

```bash
scripts/start_local.sh
scripts/run_in_zeit_env.sh uvicorn app.main:app --reload
scripts/run_in_zeit_env.sh pytest -q
```

## Deployment Notes

- The active deploy root is the repository root: `zeit-project/`.
- `Dockerfile` lives at the repo root and copies the app from that root into `/app` in the image.
- The Docker image now defaults `ZEIT_DATABASE_URL` to `sqlite:////data/test.db` and declares `/data` as a volume so schedule runs can persist outside the image layer.
- Static assets are served by FastAPI from `app/static` at `/static`, and the UI now resolves app routes with `request.url_for(...)` so links remain correct if the app is mounted behind a proxy path.
- If Railway ever renders unstyled HTML again while the app otherwise loads, the likely causes are:
  - browser cache serving an old HTML shell or CSS response
  - a Railway service pointing at the wrong root directory or an older deployment
  - a proxy/root-path mismatch outside the container rather than missing local files in this repo

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

## Docker Persistence

Build the image:

```bash
docker build -t zeit-project .
```

Run it with a named Docker volume so the SQLite database, generated blocks, and schedule run logs survive container replacement:

```bash
docker volume create zeit_data

docker run -p 8000:8000 \
  -v zeit_data:/data \
  zeit-project
```

Or use a bind mount if you want to inspect the SQLite file directly from the repo:

```bash
mkdir -p data

docker run -p 8000:8000 \
  -v "$(pwd)/data:/data" \
  zeit-project
```

You can also use Docker Compose:

```bash
cp .env.example .env
docker compose up --build
```

That uses the named volume declared in [docker-compose.yml](/Users/alexandresepulvedadedietrich/Code/zeit-project/docker-compose.yml:1), so the SQLite database survives container replacement.

## Railway Persistence

For Railway, prefer Postgres over SQLite. Local container files are not a reliable persistence layer across redeploys.

1. Add a PostgreSQL service in Railway.
2. Copy the connection string from that service.
3. Set `ZEIT_DATABASE_URL` on the app service to that Postgres URL.
4. Set `ZEIT_ENV=prod`.
5. Redeploy the app.

Example:

```env
ZEIT_ENV=prod
ZEIT_DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DBNAME
```

The app will create the schema on startup against that database, and tasks, blocks, and schedule run logs will persist across Railway restarts and deployments.

## Data Model

Core entities live in `app/db/models.py` and mirror the planned scheduling workflow:

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

See `RECRUITER_READINESS.md` for a concise review of what the repo now demonstrates well and what remains worth improving before a broader portfolio push.
