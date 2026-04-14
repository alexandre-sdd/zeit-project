#!/usr/bin/env bash
set -euo pipefail

if ! command -v conda >/dev/null 2>&1; then
  echo "conda is required to run the Zeit OR-Tools environment." >&2
  exit 1
fi

if [ "$#" -eq 0 ]; then
  echo "Usage: scripts/run_in_zeit_env.sh <command> [args...]" >&2
  echo "Example: scripts/run_in_zeit_env.sh uvicorn app.main:app --reload" >&2
  exit 1
fi

conda run -n zeit "$@"
