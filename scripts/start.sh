#!/usr/bin/env bash
# Start the Groundwork API in the background (uvicorn on 127.0.0.1:8000).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API="$ROOT/api"
PID_FILE="$API/.groundwork-server.pid"
LOG_FILE="$API/.groundwork-server.log"
VENV_PY="$API/venv/bin/python"

die() { echo "error: $*" >&2; exit 1; }

[[ -x "$VENV_PY" ]] || die "run setup first: bash scripts/setup.sh (missing $VENV_PY)"

if [[ -f "$PID_FILE" ]]; then
  pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
    echo "Groundwork API already running (PID $pid). Logs: $LOG_FILE"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

cd "$API"
nohup "$VENV_PY" -m uvicorn main:app --host 127.0.0.1 --port 8000 >>"$LOG_FILE" 2>&1 &
echo $! >"$PID_FILE"

echo "Started Groundwork API (PID $(cat "$PID_FILE"))."
echo "  URL:  http://127.0.0.1:8000/docs"
echo "  Log:  $LOG_FILE"
echo "  Stop: make stop  or  bash scripts/stop.sh"
