# Zeit Readiness

## Summary

Zeit presents as a real end-to-end demo rather than just an architecture skeleton. A user can open the app, reset a seeded scenario, generate a schedule, and see both planned work and unscheduled tasks in one pass.

The strongest signal is the combination of clean backend boundaries and a tangible product flow. The weak point is still depth: the scheduler is intentionally narrow, there is no auth or multi-user story, and the persistence/tooling layer is still prototype-grade.

## What This Repo Shows Well

- Clean package boundaries and a sensible backend architecture.
- Modern FastAPI and SQLAlchemy usage with environment-backed configuration.
- A data model that matches the scheduling domain instead of generic CRUD tables.
- A user friendly UI instead of an API-only prototype.
- A concrete scheduling flow with persisted blocks and explicit unscheduled reasons.
- Automated tests that a reviewer can run immediately.

## What Was Added In This Pass

- Deterministic demo seeding and reset behavior for one local user and one workweek.
- Event, block, reset, and schedule-generation endpoints alongside the task API.
- A server-rendered demo page with seeded inputs, schedule generation, and output panels.
- A scheduler that respects hard events, hard due dates, and workday limits, while surfacing unscheduled tasks clearly.
- Solver, API, and UI tests that validate the main demo flow.
- Lightweight repo tooling configuration for linting and CI.

## Remaining Risks Before Sharing Broadly

- There are still no update/delete flows for tasks or events in the UI.
- The scheduler is intentionally constrained to one Monday-Friday planning window and contiguous blocks.
- Alembic migrations are still missing, so schema evolution is not production-grade.
- Authentication, authorization, and multi-user constraints are not addressed.
- SQLite is fine for a prototype, but it signals local development rather than production readiness.
- OR-Tools is runtime-sensitive on Python 3.13, so the app includes a deterministic fallback scheduler for compatibility.

## Recommended Next Steps

1. Add update/delete interactions for tasks and events.
   The current add-and-reset flow is enough for a demo, but fuller editing would make the product feel less staged.

2. Improve persistence discipline.
   Add Alembic migrations and stop relying on `create_all()` as the primary schema workflow.

3. Deepen the scheduler.
   Add task splitting, configurable planning windows, and richer objective tuning once the current demo narrative is stable.

4. Add more operational polish.
   Expand linting/static analysis and add a small seed or demo script for one-command local setup.

5. Extend tests around edge behavior.
   Add checks for soft due-date ordering, event boundaries across days, and UI editing scenarios.

## Frame of the project

Present Zeit as a backend-heavy product prototype for an intelligent scheduling assistant, not as a finished startup product. The strongest pitch is:

- Designed a clean service boundary between HTTP, persistence, domain logic, and optimization
- Modeled a non-trivial scheduling domain
- Turned the prototype into a runnable, testable end-to-end demo with a clear user story