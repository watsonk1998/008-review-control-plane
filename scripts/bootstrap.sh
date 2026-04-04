#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT/apps/api"
WEB_DIR="$ROOT/apps/web"

cd "$ROOT"

if [[ ! -d "$API_DIR/.venv" ]]; then
  python3 -m venv "$API_DIR/.venv"
fi

source "$API_DIR/.venv/bin/activate"
pip install --upgrade pip setuptools wheel
pip install --no-build-isolation -e "$API_DIR[dev]"
deactivate

cd "$WEB_DIR"
npm install

echo "Bootstrap completed."
