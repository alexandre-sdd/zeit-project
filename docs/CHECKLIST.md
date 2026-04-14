# Zeit Checklist

## Current Findings

### 1. Migration discipline

Status:
- `create_all()` was previously the primary schema path
- local SQLite repair could be destructive

What to do:
- use Alembic as the source of truth for schema changes
- create a new revision for every schema change
- stop adding columns/tables without a migration
- keep startup on `upgrade head`

Done in this pass:
- added Alembic config and initial migration
- changed startup to apply migrations programmatically
- replaced silent destructive rebuild with an explicit failure on stale unmanaged SQLite schemas

### 2. Time handling

Status:
- UI renders browser-local times from naive datetimes
- `User.timezone` is not driving scheduling or rendering

What to do:
- choose a single timezone policy
- either store UTC and convert for display, or store timezone-aware datetimes consistently
- make UI rendering explicitly use the planning timezone
- add tests for timezone-sensitive rendering

### 3. Diagnostics payload size

Status:
- persisted run logs now include raw solver traces
- the latest logs are embedded into the initial page payload

What to do:
- lazy-load heavy diagnostics only when the panel opens
- keep a light summary in the first page render
- consider pagination or “load one run” behavior for large traces

### 4. CP-SAT diagnostics depth

Status:
- greedy fallback diagnostics are rich
- CP-SAT diagnostics are useful but less explanatory

What to do:
- add richer CP-SAT run metadata where available
- capture more model-level objective detail
- consider trace summarization that compares why one task was present and another absent

### 5. Block-to-run linkage

Status:
- run logs persist snapshots
- generated blocks are not linked back to a `schedule_run_id`

What to do:
- decide whether full audit history matters
- if yes, add `schedule_run_id` to generated blocks in a future migration

### 6. Owner diagnostics UX

Status:
- diagnostics are owner-oriented and technically useful
- the main trace is still raw JSON

What to do:
- add per-task expand/collapse
- add search by task name
- add “copy run JSON”
- add shortcut views for:
  - task order
  - blockers
  - unscheduled root cause

### 7. Deployment hygiene

Status:
- local Docker persistence is documented
- Railway uses Postgres

What to do:
- keep local SQLite for normal dev
- keep Railway Postgres for deployed persistence
- avoid pointing local development at production Postgres except for intentional debugging

## Suggested Next Sequence

1. Improve diagnostics loading so the initial page does not ship the full heavy trace bundle.
2. Make timezone handling explicit in both persistence and rendering.
3. Add owner tools to inspect one task’s scheduling trace quickly.
4. Decide whether blocks need a direct `schedule_run_id`.
5. Add more solver tests around diagnostics semantics, not just diagnostics presence.
