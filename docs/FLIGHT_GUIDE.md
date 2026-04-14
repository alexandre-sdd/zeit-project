# In-Flight Builder Guide

This document is a handrail for working on the Zeit project while offline. It assumes minimal FastAPI/SQLAlchemy background and focuses on concrete copy/paste steps you can execute on the plane. Follow the sections sequentially; stop after any section if time runs out.

---

## 0. TL;DR Checklist

1. **Prep once** (ideally before boarding): install Python 3.11, `pip install virtualenv`, download VS Code + extensions, and clone this repo from GitHub so everything is local.
2. **Create a virtual environment**, install dependencies, and confirm `pytest` passes.  
3. **Initialize the SQLite DB** and inspect the tables so you know the schema is ready.  
4. **Run the FastAPI server** with `uvicorn` and hit the `/health` and `/tasks` endpoints via curl or `httpie`.  
5. **Tackle one backlog item** (CRUD for events, seed script, or solver stub). Use the “Focus Tracks” section to pick the next move.  
6. **Journal what you finished** in `journaling.md` to keep continuity for the next sprint.

---

## 1. Understand the Repo Layout

```
app/
  api/        # FastAPI routes and schemas (/health, /tasks)
  core/       # Settings, logging, timezone helper
  db/         # SQLAlchemy models & session
  domain/     # Pydantic-free dataclasses for solver/services
  services/   # Planning + ICS glue code
  solver/     # CP-SAT + heuristics placeholders
  tests/      # pytest suite covering API and ICS smoke paths
scripts/       # automation helpers (DB visualizer lives here)
```

Remember: API ↔ services ↔ domain ↔ solver. Try not to mix SQLAlchemy models directly into solver/service code so later refactors stay clean.

---

## 1.1 How the Pieces Fit Together

Think about the system in four concentric circles:

1. **Transport (FastAPI)** — accepts HTTP requests, validates payloads, and converts them into domain-level inputs. Lives in `app/api/`.
2. **Services** — orchestrate higher-level workflows. Example: `plan_schedule` grabs tasks/events, calls the solver, and returns ordered `Block` objects. Lives in `app/services/`.
3. **Domain** — pure dataclasses (`app/domain/entities.py`) that describe `Task`, `Event`, `Block`, etc. They are independent from persistence or HTTP so you can reuse them in tests, solver, or CLI tools.
4. **Infrastructure** — database layer (`app/db/`), solver (`app/solver/`), and utilities (`app/core/`). These are the “adapters” that talk to SQLite, OR-Tools, timezone helpers, logging, etc.

**Typical request flow**:

```
/tasks POST
   ↓ FastAPI router (app/api/routes.py)
   ↓ DB session via get_db()
   ↓ SQLAlchemy model (app/db/models.py.Task)
   ↓ Commit to SQLite (test.db) and return a validated API response model
```

**Planning flow** (once implemented):

```
Client calls /plan/generate
   ↓ FastAPI endpoint
   ↓ Service loads Task/Event rows → converts to domain entities
   ↓ Solver builds candidate schedule (CP-SAT or heuristic)
   ↓ Service persists resulting Block rows + returns summary/ICS
   ↓ Client optionally hits /plan/ics to export to calendar
```

**Why keep layers separate?**
- Swapping SQLite → Postgres later only touches `app/db/`.
- Adding a CLI or background worker reuses the same services/domain objects.
- Tests can mock services without running FastAPI or the database.

Keep this mental map handy when editing files. If you’re unsure “where should this logic live?”, ask:
- Does it deal with HTTP specifics? → API layer.
- Does it manipulate ORM objects? → DB layer or repository helper.
- Is it pure scheduling math? → Solver.
- Does it coordinate multiple subsystems? → Service.

---

## 2. Environment Setup (offline-friendly)

Run everything from the repo root.

```bash
# 1) create + activate virtualenv
python3 -m venv .venv
source .venv/bin/activate

# 2) upgrade pip (optional but helpful)
python -m pip install --upgrade pip

# 3) install dependencies
pip install -r requirements.txt

# 4) sanity check
pytest
```

Tips:
- If `pip install` fails because of `psycopg2-binary`, add the `--no-binary` flag or skip it (not needed for SQLite).  
- When in doubt, re-run `source .venv/bin/activate` to ensure you are inside the virtual environment.

---

## 3. Database Bootstrap & Inspection

SQLite lives in `test.db`. Create tables and open a Python shell to inspect them.

```bash
# create tables
python - <<'PY'
from app.db.session import init_db
init_db()
print("DB ready!")
PY
```

Verify the schema quickly:

```bash
python - <<'PY'
from app.db.session import SessionLocal
from app.db import models

session = SessionLocal()
print("Users:", session.query(models.User).count())
print("Tasks:", session.query(models.Task).count())
print("Events:", session.query(models.Event).count())
session.close()
PY
```

To visualize the tables, run the ER-diagram helper (generates PNG/PDF under `app/output/`):

```bash
python app/db_visualizer.py
```

---

## 4. Running the API Locally

Start FastAPI via uvicorn:

```bash
uvicorn app.main:app --reload
```

Hit the existing endpoints from another terminal:

```bash
# health check
curl "http://127.0.0.1:8000/health"

# list tasks (empty at first)
curl "http://127.0.0.1:8000/tasks"

# create a task
curl -X POST "http://127.0.0.1:8000/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "title": "Write solver stub",
    "est_duration_min": 60,
    "priority": 1
  }'
```

You can also open the interactive docs at <http://127.0.0.1:8000/docs> once the server is running.

---

## 5. Focus Tracks for Offline Progress

Pick one of these depending on how much time you have in the air.

### Track A — Finish CRUD Foundations
- Add `/events` list/create endpoints mirroring the `/tasks` implementation.  
- Extend the existing Pydantic request/response models to cover events and blocks.  
- Add stronger pytest coverage for query filtering, invalid payloads, and startup behavior.

### Track B — Seed Data & ICS Export
- Write `scripts/seed_week.py` that inserts a realistic week (classes, travel, 10 tasks).  
- Call `app.services.calendar_export.blocks_to_ics` with sample `Block` data and dump the result to `output/plan.ics`, then import it into a calendar when back online.  
- Update the README with “How to generate ICS” instructions.

### Track C — Solver Skeleton
- In `app/solver/cp_sat_model.py`, start by returning placeholder `Block` objects that map each task to a simple sequential schedule (no overlaps).  
- Add three property tests in `app/tests/`:
  1. Sum of block durations equals sum of task durations.  
  2. Blocks never overlap fixed events.  
  3. Hard due tasks finish before `due_at`.  
- Once the tests pass, you have a harness ready for the real CP-SAT model.

### Track D — Quality & Tooling
- Add `pyproject.toml` with black/ruff/mypy configs and wire a `scripts/lint.sh` helper.  
- Create a GitHub Actions workflow file (`.github/workflows/ci.yml`) that runs lint + pytest so you meet the Quality Plan target once back online.

---

## 6. Journaling & Next-Day Handoff

After each plane session:

1. Append a short note to `journaling.md` (date, what you tried, blockers).  
2. Run `git status` and capture the diff you want to keep.  
3. Commit locally with a clear message (e.g., `git commit -am "Add events CRUD"`). Push once you regain connectivity.

---

## 7. Quick Troubleshooting

- **Import errors** → confirm `python -m pip list` shows FastAPI/SQLAlchemy, and that you activated `.venv`.  
- **Database locked** → stop the server, delete `test.db`, re-run `init_db()`.  
- **Timezones weird** → use UTC in the DB and convert at the edges via `app/core/timezone.py`.  
- **Can’t remember commands** → keep this file and `README.md` open in your editor; both are self-contained references.

Safe travels and happy building! Once you land, sync your work, review the PMP backlog, and plan the next sprint. 
