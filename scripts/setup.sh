#!/usr/bin/env bash
# One-time (or repeat-safe) setup: Python venv + deps, optional .env, extension npm build.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API="$ROOT/api"
EXT="$ROOT/extension"
WEB="$ROOT/web"
PY="${PYTHON:-python3}"

die() { echo "error: $*" >&2; exit 1; }

command -v "$PY" >/dev/null 2>&1 || die "need $PY on PATH (install Python 3.10+)"

if ! "$PY" -c 'import sys; assert sys.version_info >= (3, 10)' 2>/dev/null; then
  die "need Python 3.10 or newer (found $($PY --version 2>&1))"
fi

echo "==> Python venv at api/venv"
if [[ ! -d "$API/venv" ]]; then
  "$PY" -m venv "$API/venv"
fi
# shellcheck source=/dev/null
source "$API/venv/bin/activate"
python -m pip install -U pip
pip install -r "$API/requirements.txt"

echo "==> api/.env"
if [[ ! -f "$API/.env" ]]; then
  if [[ -f "$API/.env.example" ]]; then
    cp "$API/.env.example" "$API/.env"
  else
    echo "ANTHROPIC_API_KEY=" >"$API/.env"
  fi
fi
if [[ -t 0 ]] && ! grep -qE '^ANTHROPIC_API_KEY=.+' "$API/.env" 2>/dev/null; then
  read -rsp "Enter ANTHROPIC_API_KEY (hidden; leave empty to set later in api/.env): " key
  echo
  if [[ -n "${key:-}" ]]; then
    printf '%s\n' "ANTHROPIC_API_KEY=$key" >"$API/.env"
    echo "    Wrote key to $API/.env"
  else
    echo "    Add ANTHROPIC_API_KEY to $API/.env before /analyse will work."
  fi
elif ! grep -qE '^ANTHROPIC_API_KEY=.+' "$API/.env" 2>/dev/null; then
  echo "    $API/.env has no API key yet — edit it before /analyse will work."
else
  echo "    $API/.env already has ANTHROPIC_API_KEY set."
fi

if command -v npm >/dev/null 2>&1; then
  echo "==> Extension (npm install + compile)"
  (cd "$EXT" && npm install && npm run compile)
  if [[ -f "$WEB/package.json" ]]; then
    echo "==> Web app (npm install)"
    (cd "$WEB" && npm install)
  fi
else
  echo "==> Skipping Node builds: npm not on PATH"
  echo "    Install Node.js, then run: (cd extension && npm install && npm run compile)"
  echo "    and: (cd web && npm install)"
fi

echo ""
echo "Setup done."
echo "  Start API only: make start"
echo "  Start web UI:   make start-web   (needs API on :8000 for /api proxy)"
echo "  Start both:      make start-all"
echo "  Stop both:       make stop"
