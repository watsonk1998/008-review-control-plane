#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/lucas/repos/review/008-review-control-plane"
API_DIR="$ROOT/apps/api"
VERIFY_DIR="$ROOT/artifacts/verification"
mkdir -p "$VERIFY_DIR"

export DEEPTUTOR_BASE_URL="${DEEPTUTOR_BASE_URL:-http://127.0.0.1:8121}"
export GPT_RESEARCHER_EXTERNAL_PATH="${GPT_RESEARCHER_EXTERNAL_PATH:-/tmp/008-discovery/gpt-researcher}"
export FASTGPT_VERIFICATION_DATASET_ID="${FASTGPT_VERIFICATION_DATASET_ID:-6984435295a6ce02e80696a1}"

cd "$API_DIR"
source .venv/bin/activate

python - <<PY
import asyncio, json, os, pathlib, requests, time
from src.adapters.fastgpt_adapter import FastGPTAdapter, FastGPTResponseParseError
from src.adapters.gpt_researcher_adapter import GPTResearcherAdapter
from src.adapters.llm_gateway import LLMGateway
from src.adapters.deeptutor_adapter import DeepTutorAdapter

ROOT = pathlib.Path("/Users/lucas/repos/review/008-review-control-plane")
VERIFY_DIR = ROOT / "artifacts" / "verification"
DOC = str(ROOT / "fixtures" / "copied" / "supervision" / "230235-冷轧厂2030单元三台行车电气系统改造-施工组织设计.docx")
API_BASE = "http://127.0.0.1:8018"
DATASET_ID = os.getenv("FASTGPT_VERIFICATION_DATASET_ID", "6984435295a6ce02e80696a1")

async def main():
    llm = LLMGateway()
    fast = FastGPTAdapter()
    deeptutor = DeepTutorAdapter(os.getenv("DEEPTUTOR_BASE_URL", "http://127.0.0.1:8121"))
    gptr = GPTResearcherAdapter()

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

    dt_health = await deeptutor.health_check()
    dt_answer = await deeptutor.ask_knowledge_question("施工组织设计中的安全管理章节通常包含哪些内容？")
    (VERIFY_DIR / "deeptutor-connectivity.json").write_text(json.dumps({"health": dt_health, "sample": dt_answer}, ensure_ascii=False, indent=2), encoding="utf-8")

    gptr_health = await gptr.health_check()
    gptr_payload = {"health": gptr_health}
    try:
        local_report = await gptr.run_local_docs_research("请基于该施工组织设计文档提炼项目概况和关键风险。", [DOC])
        gptr_payload["localDocs"] = {"meta": local_report.get("meta"), "reportPreview": local_report.get("report", "")[:3000]}
    except Exception as exc:
        gptr_payload["localDocsError"] = str(exc)
    (VERIFY_DIR / "gpt-researcher-connectivity.json").write_text(json.dumps(gptr_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    created = requests.post(f"{API_BASE}/api/tasks", json={
        "taskType": "knowledge_qa",
        "capabilityMode": "deeptutor",
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
