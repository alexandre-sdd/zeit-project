# Zeit Architecture

## Purpose

Zeit is a backend-heavy scheduling prototype. The application takes a one-week planning problem made of tasks, fixed events, and workday constraints, then produces a persisted schedule and a persisted diagnostics trace that explains how the solver behaved.

This document explains:
- what each major part of the application is for
- what talks to what
- what payloads move between layers
- which technology is used at each layer

## Stack

- Web framework: FastAPI
- Templating: Jinja2
- Persistence: SQLAlchemy ORM
- Databases:
  - local development: SQLite
  - deployed persistence: PostgreSQL
- Migrations: Alembic
- Solver:
  - preferred: OR-Tools CP-SAT
  - fallback: deterministic greedy scheduler
- Frontend: server-rendered HTML with plain JavaScript and CSS
- Tests: pytest with FastAPI `TestClient`

## Runtime Flow

1. The app starts in [app/main.py](/Users/alexandresepulvedadedietrich/Code/zeit-project/app/main.py:1).
2. Startup calls `configure_logging()` and `init_db()`.
3. `init_db()` runs Alembic migrations to `head` against the configured database.
4. FastAPI serves:
   - JSON APIs for tasks, events, blocks, schedule generation, and schedule run logs
   - the demo page at `/`
5. When a schedule is generated:
   - tasks and events are loaded from the database
   - the solver builds a schedule
   - generated blocks are persisted
   - a `ScheduleRun` record is persisted with the solver trace
6. The UI can then render both the calendar result and the diagnostics payload.

## Code Map

### `app/main.py`

Purpose:
- create the FastAPI app
- configure startup lifecycle
- mount static assets
- attach routes

Technology:
- FastAPI

### `app/api/`

Files:
- [app/api/routes.py](/Users/alexandresepulvedadedietrich/Code/zeit-project/app/api/routes.py:1)
- [app/api/schemas.py](/Users/alexandresepulvedadedietrich/Code/zeit-project/app/api/schemas.py:1)

Purpose:
- define HTTP endpoints
- validate request payloads
- serialize ORM/domain objects into API responses

Technology:
- FastAPI routing
- Pydantic models

Main payloads:
- `TaskCreate` / `TaskRead`
- `EventCreate` / `EventRead`
- `BlockRead`
- `ScheduleGenerateRequest`
- `ScheduleGenerateResponse`
- `ScheduleRunRead`
- `SolverRunRead`

Important routes:
- `GET /`
- `GET /health`
- `GET/POST/DELETE /tasks`
- `GET/POST/DELETE /events`
- `GET /blocks`
- `POST /schedule/generate`
- `GET /schedule/runs`
- `POST /demo/reset`
- `GET /calendar/export.ics`

### `app/services/`

Important files:
- [app/services/planning_service.py](/Users/alexandresepulvedadedietrich/Code/zeit-project/app/services/planning_service.py:1)
- [app/services/demo_service.py](/Users/alexandresepulvedadedietrich/Code/zeit-project/app/services/demo_service.py:1)
- [app/services/schedule_policy.py](/Users/alexandresepulvedadedietrich/Code/zeit-project/app/services/schedule_policy.py:1)
- [app/services/calendar_export.py](/Users/alexandresepulvedadedietrich/Code/zeit-project/app/services/calendar_export.py:1)

Purpose:
- orchestrate use cases
- bridge ORM rows into domain objects
- own schedule-generation workflow
- own demo reset and seed behavior
- centralize workday and slot policy

Technology:
- plain Python service layer

Most important flow:
- `generate_schedule_for_user()`
  - loads `Task` and `Event` ORM rows
  - converts them into domain dataclasses
  - calls the solver
  - deletes prior generated blocks for the week
  - persists new blocks
  - persists a `ScheduleRun` diagnostics snapshot

### `app/solver/`

Important file:
- [app/solver/cp_sat_model.py](/Users/alexandresepulvedadedietrich/Code/zeit-project/app/solver/cp_sat_model.py:1)

Purpose:
- implement the actual scheduling logic
- choose between CP-SAT and greedy fallback
- return both schedule results and solver diagnostics

Technology:
- OR-Tools CP-SAT when available
- deterministic Python fallback when OR-Tools cannot run

Inputs:
- `list[Task]`
- `list[Event]`
- `week_start`
- optional workday overrides

Output:
- `ScheduleResult`
  - `blocks`
  - `unscheduled_tasks`
  - `solver_run`

Solver diagnostics now include:
- task order
- per-task traces
- valid windows
- chosen windows
- rejected attempts and blockers
- CP-SAT solve status metadata

### `app/domain/`

Important file:
- [app/domain/entities.py](/Users/alexandresepulvedadedietrich/Code/zeit-project/app/domain/entities.py:1)

Purpose:
- define transport-neutral domain dataclasses

Technology:
- Python dataclasses

These are the types passed between the service layer and the solver:
- `Task`
- `Event`
- `Block`
- `UnscheduledTask`
- `SolverRun`
- `ScheduleResult`

### `app/db/`

Important files:
- [app/db/models.py](/Users/alexandresepulvedadedietrich/Code/zeit-project/app/db/models.py:1)
- [app/db/session.py](/Users/alexandresepulvedadedietrich/Code/zeit-project/app/db/session.py:1)
- [app/db/base.py](/Users/alexandresepulvedadedietrich/Code/zeit-project/app/db/base.py:1)

Purpose:
- define the relational schema
- create the SQLAlchemy engine and session
- run migrations at startup

Technology:
- SQLAlchemy
- Alembic

Main tables:
- `users`
- `tasks`
- `events`
- `blocks`
- `schedule_runs`

### `app/templates/` and `app/static/`

Important files:
- [app/templates/index.html](/Users/alexandresepulvedadedietrich/Code/zeit-project/app/templates/index.html:1)
- [app/static/demo.css](/Users/alexandresepulvedadedietrich/Code/zeit-project/app/static/demo.css:1)

Purpose:
- render the demo UI
- collect user inputs
- call JSON APIs from the browser
- render calendar, queue, unscheduled tasks, and diagnostics

Technology:
- Jinja2 HTML
- vanilla JavaScript
- CSS

Browser-side responsibilities:
- preview workday window changes
- submit schedule generation requests
- intercept task/event remove actions and call the JSON delete APIs without a full page reload
- render returned blocks and unscheduled tasks
- fetch persisted schedule run logs
- display raw diagnostics JSON for owner/debug use

Delete-control design:
- the tasks/events "Remove" controls are rendered as real links in the HTML
- normal operation uses JavaScript to intercept the click and issue `DELETE /tasks/{id}` or `DELETE /events/{id}`
- after a successful delete, the page removes the row locally, updates counts, and redraws the dashboard in place
- the link target remains a server-side fallback route so the control still works if browser-side JavaScript fails

## Primary Data Shapes

### Task payload

Stored in DB:
- `id`
- `user_id`
- `title`
- `est_duration_min`
- `due_at`
- `due_is_hard`
- `priority`
- `category`
- `preferred_location`
- `repeat_rule`

Used by solver:
- duration
- due date hardness
- priority
- title as final tie-breaker

### Event payload

Stored in DB:
- `id`
- `user_id`
- `title`
- `starts_at`
- `ends_at`
- `location`
- `lock_level`
- `source`

Used by solver:
- occupies time as fixed/busy intervals

### Block payload

Stored in DB:
- `id`
- `user_id`
- `task_id`
- `event_id`
- `starts_at`
- `ends_at`
- `location`
- `status`
- `lock_level`
- `generated_by`

Represents:
- persisted task placements returned by the solver

### ScheduleRun payload

Stored in DB as JSON text fields:
- `constraints_json`
- `tasks_to_plan_json`
- `planned_tasks_json`
- `unplanned_tasks_json`
- `solver_json`
- `solution_json`

Purpose:
- keep a complete run snapshot for owner/developer diagnosis

## Interaction Map

### Schedule generation

`Browser`
-> `POST /schedule/generate`
-> `routes.generate_schedule()`
-> `planning_service.generate_schedule_for_user()`
-> `solver.build_schedule()`
-> `cp_sat_model._build_schedule_cp_sat()` or `_build_schedule_greedy()`
-> persist `Block`
-> persist `ScheduleRun`
-> return `ScheduleGenerateResponse`
-> browser renders calendar + queue + unscheduled list
-> browser refreshes `GET /schedule/runs`

### Diagnostics view

`Browser`
-> `GET /schedule/runs`
-> `routes.get_schedule_runs()`
-> `planning_service.list_schedule_runs()`
-> JSON payload returned
-> UI renders summary and raw trace JSON

## Environment Model

### Local development

- default DB: SQLite
- default file: `test.db`
- runtime may use greedy fallback if Python 3.13 is active

### Local container

- default DB: SQLite at `/data/test.db`
- persistence requires Docker bind mount or named volume

### Railway / deployed app

- expected DB: PostgreSQL
- persistence via `ZEIT_DATABASE_URL`
- CP-SAT is more likely to be available depending on runtime

## Current Boundaries

Good boundaries already in place:
- API does not contain scheduling logic
- solver does not know about ORM sessions
- service layer converts between ORM and domain
- diagnostics persistence is owned by the planning service

Current limitations:
- no task splitting
- one-week planning frame
- naive datetime handling
- migrations are now present, but only initial schema discipline exists
- diagnostics are detailed but still mostly raw for owner use
