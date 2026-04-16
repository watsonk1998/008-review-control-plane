#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT/apps/api"
WEB_DIR="$ROOT/apps/web"
MODE="${1:-all}"
API_PORT="${API_PORT:-8018}"
WEB_PORT="${WEB_PORT:-3008}"
NEXT_PUBLIC_API_BASE_URL="${NEXT_PUBLIC_API_BASE_URL:-http://127.0.0.1:${API_PORT}}"

run_api() {
  cd "$API_DIR"
  source .venv/bin/activate
  uvicorn src.main:app --host 127.0.0.1 --port "$API_PORT"
}

run_web() {
  cd "$WEB_DIR"
  NEXT_PUBLIC_API_BASE_URL="$NEXT_PUBLIC_API_BASE_URL" npm run dev -- --port "$WEB_PORT"
}

case "$MODE" in
  api)
    run_api
    ;;
  web)
    run_web
    ;;
  all)
    run_api &
    API_PID=$!
    sleep 3
    run_web &
    WEB_PID=$!
    trap 'kill "$WEB_PID" "$API_PID" >/dev/null 2>&1 || true' EXIT INT TERM
    wait
    ;;
  *)
    echo "Usage: $0 [api|web|all]" >&2
    exit 1
    ;;
esac
