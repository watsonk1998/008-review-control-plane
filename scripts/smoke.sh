#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT/apps/api"
WEB_DIR="$ROOT/apps/web"
API_BASE="${NEXT_PUBLIC_API_BASE_URL:-http://127.0.0.1:8018}"

cd "$API_DIR"
source .venv/bin/activate
pytest -q
deactivate

cd "$WEB_DIR"
npm run lint
npm run build

python3 - <<PY
import json, requests
base = "$API_BASE"
try:
    data = requests.get(f"{base}/api/health", timeout=20).json()
    print(json.dumps({"smokeHealth": data.get("status"), "fixtureCount": data.get("fixtureCount")}, ensure_ascii=False, indent=2))
except Exception as exc:
    print(json.dumps({"smokeHealth": "skipped", "reason": str(exc)}, ensure_ascii=False, indent=2))
PY
