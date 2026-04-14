#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

port="${PORT:-8000}"

if [ -x ".venv/bin/uvicorn" ]; then
  exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "$port" --reload "$@"
fi

exec uvicorn app.main:app --host 127.0.0.1 --port "$port" --reload "$@"
