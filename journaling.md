# Journal note-taking

## Learning section

First created the PMP and data structure

### 24 Oct 2025
Used the project PMP to craft a first skeleton for the app structure:
FastAPI - SQLite - SQLQlchemy and Optimisation OR-tools for optimisation

Created promer Git repo and link to online github repository

### 25 Oct 2025
Begin to learn the framework, start by understanding data structure, SQLite + SQLAlchemy
Shaped the `zeit/` project structure (api/core/db/domain/solver/services/tests) and added scaffolding modules for domain entities, solver, and services. Captured the initial relational schema (users, events, tasks, blocks) in SQLAlchemy models and documented it in the README.

### 26 Oct 2025
Contimue on exploring data structure, created script to visualize data base `db_vizualiser.db`

### 13 Apr 2026
Expanded the demo from a simple schedule generator into a more inspectable planning tool.
Added adjustable workday windows in the UI and updated the schedule surface so the queue, calendar, and diagnostics panels are easier to inspect during a run.

### 14 Apr 2026
Added persistent schedule run logging for each generated plan.
Each run now stores constraints, tasks sent to the solver, planned tasks, unplanned tasks, solver metadata, and the final solution snapshot.

Added developer-facing diagnostics traces so a run can be diagnosed after the fact.
The logs now capture task ordering, valid windows, attempted placements, blockers, and chosen windows for the greedy fallback, plus structured task-level diagnostics for the CP-SAT path.

Updated deployment and persistence setup:
- Docker now defaults the SQLite path to `/data/test.db`
- added `.env.example` and `docker-compose.yml`
- documented Docker volume persistence for local runs
- documented Railway Postgres persistence for deployed runs

Connected the deployed app to Railway Postgres so generated schedules and run logs persist across redeploys.

Stabilized local delete behavior in the demo UI.
Task and event removal now use async JavaScript again for in-place updates, but keep a server-side fallback route underneath so the controls still work if browser-side handling fails.
