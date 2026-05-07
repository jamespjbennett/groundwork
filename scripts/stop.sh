#!/usr/bin/env bash
# Stop background processes started by scripts/start.sh and start-web.sh.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API="$ROOT/api"
WEB="$ROOT/web"

stop_pidfile() {
  local name="$1" file="$2"
  if [[ ! -f "$file" ]]; then
    return 0
  fi
  local pid
  pid="$(cat "$file" 2>/dev/null || true)"
  rm -f "$file"
  if [[ -z "${pid:-}" ]]; then
    return 0
  fi
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    echo "Stopped Groundwork $name (PID $pid)."
  else
    echo "Removed stale $name PID file (process $pid not running)."
  fi
}

any=false
[[ -f "$WEB/.groundwork-web.pid" ]] && any=true
[[ -f "$API/.groundwork-server.pid" ]] && any=true

stop_pidfile "web" "$WEB/.groundwork-web.pid"
stop_pidfile "API" "$API/.groundwork-server.pid"

if [[ "$any" == false ]]; then
  echo "Nothing to stop (no PID files from make start / make start-web)."
fi
