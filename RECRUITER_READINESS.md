# Zeit Recruiter Readiness

## Summary

Zeit already presents well as an architecture-first backend prototype. The strongest signal in the repository is the separation between API, domain, persistence, services, and solver logic. That separation makes the code easy to discuss in an interview because the intent is clearer than in a single-file prototype.

The weak point is not code quality so much as feature completeness. A reviewer can see that the scheduling engine is still a placeholder, the API surface is narrow, and the developer tooling is still minimal. That is fine if you frame the repo honestly as an early-stage systems design and backend foundations exercise.

## What This Repo Shows Well

- Clean package boundaries and a sensible backend architecture.
- Modern FastAPI and SQLAlchemy usage with environment-backed configuration.
- A data model that matches the scheduling domain instead of generic CRUD tables.
- Basic automated tests that a reviewer can run immediately.
- Useful extension seams for scheduling, exports, and future integrations.

## What Was Cleaned Up In This Pass

- Updated settings to work with the current Pydantic v2 stack.
- Moved database initialization into the FastAPI startup lifecycle instead of running it at import time.
- Switched `/tasks` creation to a typed JSON contract with explicit validation and response models.
- Added a `/health` endpoint for smoke checks.
- Added API and service tests so the repo has runnable verification.
- Added a correctly named schema visualizer entrypoint while preserving backward compatibility with the old filename.
- Tightened the README so the current scope is accurate and easy to explain.

## Remaining Risks Before Sharing Broadly

- `app/solver/cp_sat_model.py` still returns an empty schedule, which makes the core product promise unimplemented.
- There are no endpoints yet for events, blocks, or schedule generation.
- The project does not yet show migrations, CI, linting, or static analysis.
- Authentication, authorization, and multi-user constraints are not addressed.
- SQLite is fine for a prototype, but it signals local development rather than production readiness.

## Recommended Next Steps

1. Implement one end-to-end planning flow.
   Add event CRUD, a schedule-generation endpoint, and a minimal non-empty scheduling strategy even if it is heuristic rather than optimal.

2. Add developer-quality signals.
   Create a `pyproject.toml` with Ruff and pytest settings, then add a small CI workflow that runs tests on push.

3. Show one stronger piece of business logic.
   A simple scheduler that respects fixed events and places tasks by priority would make the project materially more impressive than a placeholder solver.

4. Improve persistence discipline.
   Add Alembic migrations and stop relying on `create_all()` as the primary schema workflow.

5. Broaden tests around behavior, not just smoke paths.
   Add tests for invalid event ranges, schedule conflicts, and ICS export edge cases.

## How To Frame It With A Recruiter

Present Zeit as a backend systems prototype for an intelligent scheduling assistant, not as a finished product. The strongest pitch is:

- you designed a clean service boundary between HTTP, persistence, domain logic, and optimization
- you modeled a non-trivial scheduling domain
- you made the prototype runnable, testable, and ready for the next implementation step

That framing is defensible and will read much better than overselling the unfinished solver.
