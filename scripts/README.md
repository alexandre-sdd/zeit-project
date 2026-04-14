# Scripts

Utility scripts for the Zeit project live here. Add automation such as
database migrations, data imports, or deployment helpers in this
directory.

- `run_in_zeit_env.sh`: run a command inside the `conda` env `zeit`, which is the local Python
  `3.12` environment where OR-Tools CP-SAT is currently verified to work.
- `start_local.sh`: start the FastAPI app from the repository root using `.venv/bin/uvicorn`
  when present, otherwise the active shell's `uvicorn`.
