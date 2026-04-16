#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT/apps/api"
VERIFY_DIR="$ROOT/artifacts/verification"
mkdir -p "$VERIFY_DIR"
export REVIEW_CONTROL_PLANE_ROOT="$ROOT"


export FASTGPT_VERIFICATION_DATASET_ID="${FASTGPT_VERIFICATION_DATASET_ID:-6984435295a6ce02e80696a1}"

cd "$API_DIR"
source .venv/bin/activate

python - <<PY
import asyncio, json, os, pathlib, requests, time
from src.adapters.fastgpt_adapter import FastGPTAdapter, FastGPTResponseParseError
from src.adapters.llm_gateway import LLMGateway

ROOT = pathlib.Path(os.environ["REVIEW_CONTROL_PLANE_ROOT"])
VERIFY_DIR = ROOT / "artifacts" / "verification"
DOC = str(ROOT / "fixtures" / "supervision" / "施工组织设计-冷轧厂2030单元三台行车电气系统改造.docx")
API_BASE = "http://127.0.0.1:8018"
DATASET_ID = os.getenv("FASTGPT_VERIFICATION_DATASET_ID", "6984435295a6ce02e80696a1")

async def main():
    llm = LLMGateway()
    fast = FastGPTAdapter()

    llm_health = await llm.health_check()
    (VERIFY_DIR / "llm-health.json").write_text(json.dumps(llm_health, ensure_ascii=False, indent=2), encoding="utf-8")

    fast_a = await fast.search_dataset_chunks(dataset_id=DATASET_ID, query="施工组织设计中安全管理应关注什么", limit=5)
    (VERIFY_DIR / "fast-mode-a.json").write_text(json.dumps(fast_a, ensure_ascii=False, indent=2), encoding="utf-8")

    collection_id = os.getenv("FASTGPT_VERIFICATION_COLLECTION_ID")
    if collection_id:
        try:
            fast_b = await fast.search_collection_chunks(collection_id=collection_id, query="安全管理", dataset_id=DATASET_ID)
            (VERIFY_DIR / "fast-mode-b.json").write_text(json.dumps(fast_b, ensure_ascii=False, indent=2), encoding="utf-8")
        except FastGPTResponseParseError as exc:
            (VERIFY_DIR / "fast-mode-b.md").write_text(f"Mode B parse failed as expected for debugging.\\n\\n{exc}", encoding="utf-8")
    else:
        (VERIFY_DIR / "fast-mode-b.md").write_text("Skipped: FASTGPT_VERIFICATION_COLLECTION_ID not provided.", encoding="utf-8")



    created = requests.post(f"{API_BASE}/api/tasks", json={
        "taskType": "knowledge_qa",
        "capabilityMode": "llm_only",
        "query": "施工组织设计中安全管理应关注哪些核心点？",
        "datasetId": DATASET_ID,
        "debug": True,
    }, timeout=60).json()
    task_id = created["id"]
    final_state = None
    for _ in range(120):
        time.sleep(2)
        final_state = requests.get(f"{API_BASE}/api/tasks/{task_id}", timeout=60).json()
        if final_state.get("status") in {"succeeded", "failed", "partial"}:
            break
    result = requests.get(f"{API_BASE}/api/tasks/{task_id}/result", timeout=60).json()
    events = requests.get(f"{API_BASE}/api/tasks/{task_id}/events", timeout=60).json()
    (VERIFY_DIR / "end-to-end-ui-or-api.json").write_text(json.dumps({"task": final_state, "result": result, "events": events}, ensure_ascii=False, indent=2), encoding="utf-8")

asyncio.run(main())
PY

echo "Verification artifacts written to $VERIFY_DIR"
