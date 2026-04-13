"""
Hermes External Server Shim.

Run this script to expose the NousResearch Hermes Agent as a FastAPI REST endpoint
compatible with the 008 Dual Review orchestrator.

Usage:
  1. pip install fastapi uvicorn pydantic
  2. pip install git+https://github.com/NousResearch/hermes-agent.git
  3. Set OPENROUTER_API_KEY (or ANTHROPIC_API_KEY / OPENAI_API_KEY) in environment.
  4. Configure Hermes API Base URL if using custom LLM gateway: `export OPENAI_BASE_URL=...`
  5. python hermes_server_shim.py
  
Then in 008's .env file, set:
  HERMES_EXTERNAL_ENDPOINT=http://127.0.0.1:8080
"""

import os
# Bypass local proxies BEFORE any other imports to avoid 403 HTML Cloudflare blocks
os.environ["NO_PROXY"] = "*"

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import logging
import json

try:
    from run_agent import AIAgent
    HERMES_AVAILABLE = True
except ImportError:
    HERMES_AVAILABLE = False
    logging.warning("Module run_agent (Hermes Agent) not found. Server will run in Mock Mode.")

app = FastAPI(title="Hermes External Endpoint for 008")

class ChatRequest(BaseModel):
    message: str
    model: str = "hermes"

@app.get("/health")
def health():
    return {"status": "ok", "hermes_installed": HERMES_AVAILABLE}

@app.post("/chat")
def chat(request: ChatRequest):
    if not HERMES_AVAILABLE:
        # Graceful mocking for immediate interface validation without installing hermes
        mock_response = {
            "overall_assessment": "[Mocked Response] 确认通讯成功，但环境中未安装由于 hermes-agent，已降级回显。",
            "grade": "pass",
            "findings": [
                {
                    "id": "H-MOCK-999",
                    "title": "Hermes 环境缺失",
                    "severity": "info",
                    "category": "completeness",
                    "summary": "请按照 hermes_server_shim.py 中的指示安装真实的 hermes-agent",
                    "suggestion": "执行 pip install git+https://github.com/NousResearch/hermes-agent.git"
                }
            ],
            "top_risks": ["未执行真实大模型推理"]
        }
        return {"response": json.dumps(mock_response, ensure_ascii=False)}

    import os
    os.environ["NO_PROXY"] = "*"

    # Auto-load century.json
    config_path = os.path.expanduser('~/control/secrets/api-keys/century.json')
    base_url = ""
    if os.path.exists(config_path):
        try:
            import json
            with open(config_path, 'r', encoding='utf-8') as f:
                century_data = json.load(f)
                sealos = century_data.get('sealos_aiproxy', {})
                api_key = sealos.get('api_key', '')
                base_url = sealos.get('base_url', '')
                if api_key:
                    os.environ["OPENAI_API_KEY"] = api_key
        except Exception as e:
            logging.error(f"Failed to load century.json: {e}")

    llm_model = "qwen-plus"

    agent = AIAgent(
        model=llm_model,
        provider="openai",
        base_url=base_url,
        api_key=api_key,
        quiet_mode=True,
        skip_context_files=True,
        skip_memory=True,
    )
    
    # 008 passes both System rules and User Content in `request.message`
    response_text = agent.chat(request.message)
    return {"response": response_text}

if __name__ == "__main__":
    print("==================================================")
    print(" Starting Hermes Gateway Shim on port 8088...")
    print(f" Hermes Engine Available: {HERMES_AVAILABLE}")
    print("==================================================")
    uvicorn.run(app, host="0.0.0.0", port=8088)
