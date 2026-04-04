#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT/apps/api"
WEB_DIR="$ROOT/apps/web"
MODE="${1:-all}"
API_PORT="${API_PORT:-8018}"
WEB_PORT="${WEB_PORT:-3008}"
BRIDGE_PORT="${DEEPTUTOR_BRIDGE_PORT:-8121}"
DEEPTUTOR_EXTERNAL_PATH="${DEEPTUTOR_EXTERNAL_PATH:-/tmp/008-discovery/DeepTutor}"
GPT_RESEARCHER_EXTERNAL_PATH="${GPT_RESEARCHER_EXTERNAL_PATH:-/tmp/008-discovery/gpt-researcher}"
NEXT_PUBLIC_API_BASE_URL="${NEXT_PUBLIC_API_BASE_URL:-http://127.0.0.1:${API_PORT}}"

run_bridge() {
  cd "$ROOT"
  "$API_DIR/.venv/bin/python" "$ROOT/scripts/run_deeptutor_bridge.py" --port "$BRIDGE_PORT" --deeptutor-path "$DEEPTUTOR_EXTERNAL_PATH"
}

run_api() {
  cd "$API_DIR"
  export DEEPTUTOR_BASE_URL="http://127.0.0.1:${BRIDGE_PORT}"
  export GPT_RESEARCHER_EXTERNAL_PATH
  source .venv/bin/activate
  uvicorn src.main:app --host 127.0.0.1 --port "$API_PORT"
}

run_web() {
  cd "$WEB_DIR"
  NEXT_PUBLIC_API_BASE_URL="$NEXT_PUBLIC_API_BASE_URL" npm run dev -- --port "$WEB_PORT"
}

case "$MODE" in
  bridge)
    run_bridge
    ;;
  api)
    run_api
    ;;
  web)
    run_web
    ;;
  all)
    run_bridge &
    BRIDGE_PID=$!
    sleep 3
    run_api &
    API_PID=$!
    sleep 3
    run_web &
    WEB_PID=$!
    trap 'kill "$WEB_PID" "$API_PID" "$BRIDGE_PID" >/dev/null 2>&1 || true' EXIT INT TERM
    wait
    ;;
  *)
    echo "Usage: $0 [bridge|api|web|all]" >&2
    exit 1
    ;;
esac
