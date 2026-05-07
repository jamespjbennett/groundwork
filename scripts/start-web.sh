#!/usr/bin/env bash
# Start the Vite dev server for the web UI (http://127.0.0.1:3000).
# API calls are proxied to :8000 as /api/* (see web/vite.config.ts).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WEB="$ROOT/web"
PID_FILE="$WEB/.groundwork-web.pid"
LOG_FILE="$WEB/.groundwork-web.log"

die() { echo "error: $*" >&2; exit 1; }

[[ -f "$WEB/package.json" ]] || die "no web app at $WEB"
command -v npm >/dev/null 2>&1 || die "need npm on PATH"
[[ -d "$WEB/node_modules" ]] || die "run make setup first (npm install in web/)"

if [[ -f "$PID_FILE" ]]; then
  pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
    echo "Groundwork web already running (PID $pid). Logs: $LOG_FILE"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

cd "$WEB"
# Single process tree; port/host match vite.config.ts
nohup npx vite --host 127.0.0.1 --port 3000 >>"$LOG_FILE" 2>&1 &
echo $! >"$PID_FILE"

echo "Started Groundwork web (PID $(cat "$PID_FILE"))."
echo "  URL:  http://127.0.0.1:3000"
echo "  Log:  $LOG_FILE"
echo "  Stop: make stop  (stops API + web)"
