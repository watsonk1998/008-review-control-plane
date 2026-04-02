#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import types

import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LLM_CONFIG_PATH = (
    Path.home() / "tools" / "from-obsidian" / "AI" / "config" / "century.json"
)
DEFAULT_LLM_PROFILE = "dashscope"
DEFAULT_LLM_MODEL = "qwen3.5-plus"
DEFAULT_DEEPTUTOR_PATH = Path("/tmp/008-discovery/DeepTutor")


def _first_non_empty(*values: str | None) -> str:
    for value in values:
        if value and str(value).strip():
            return str(value).strip()
    return ""


def resolve_llm_env() -> dict[str, str]:
    env_base = _first_non_empty(os.getenv("LLM_BASE_URL"), os.getenv("OPENAI_BASE_URL"))
    env_key = _first_non_empty(os.getenv("LLM_API_KEY"), os.getenv("OPENAI_API_KEY"))
    env_model = _first_non_empty(os.getenv("LLM_MODEL"), os.getenv("OPENAI_MODEL"))
    if env_base and env_key:
        return {
            "binding": "openai",
            "base_url": env_base.rstrip("/"),
            "api_key": env_key,
            "model": env_model or DEFAULT_LLM_MODEL,
            "profile": os.getenv("LLM_CONFIG_PROFILE", DEFAULT_LLM_PROFILE),
            "source": "env",
        }

    config_path = Path(
        os.getenv("LLM_CONFIG_PATH", str(DEFAULT_LLM_CONFIG_PATH))
    ).expanduser()
    profile = os.getenv("LLM_CONFIG_PROFILE", DEFAULT_LLM_PROFILE)
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    profile_data = payload[profile]
    models = profile_data.get("models")
    model = env_model or DEFAULT_LLM_MODEL
    if isinstance(models, dict):
        chat_models = models.get("chat")
        if isinstance(chat_models, list) and chat_models:
            model = str(chat_models[0])
        elif isinstance(chat_models, str):
            model = chat_models
    elif isinstance(models, list) and models:
        model = str(models[0])

    return {
        "binding": "openai",
        "base_url": str(profile_data["base_url"]).rstrip("/"),
        "api_key": str(profile_data["api_key"]).strip(),
        "model": model,
        "profile": profile,
        "source": "credentials_file",
    }


def prepare_deeptutor_runtime(repo_path: Path) -> None:
    llm = resolve_llm_env()
    os.environ["LLM_BINDING"] = llm["binding"]
    os.environ["LLM_HOST"] = llm["base_url"]
    os.environ["LLM_API_KEY"] = llm["api_key"]
    os.environ["LLM_MODEL"] = llm["model"]
    os.environ.setdefault("OPENAI_BASE_URL", llm["base_url"])
    os.environ.setdefault("OPENAI_API_KEY", llm["api_key"])

    if str(repo_path) not in sys.path:
        sys.path.insert(0, str(repo_path))

    # DeepTutor chat path only needs ChatAgent, but the package imports broader
    # service modules. Patch unused heavy modules so the bridge stays lightweight.
    dummy_tools = types.ModuleType("src.tools")

    async def rag_search(*args, **kwargs):
        return {"answer": ""}

    def web_search(*args, **kwargs):
        return {"answer": "", "citations": []}

    dummy_tools.rag_search = rag_search
    dummy_tools.web_search = web_search
    sys.modules["src.tools"] = dummy_tools

    for module_name in ["src.services.search", "src.services.setup", "src.services.tts"]:
        if module_name not in sys.modules:
            sys.modules[module_name] = types.ModuleType(module_name)


def create_app(repo_path: Path, session_dir: Path) -> FastAPI:
    prepare_deeptutor_runtime(repo_path)
    from src.agents.chat import ChatAgent, SessionManager

    app = FastAPI(title="DeepTutor Bridge", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    session_manager = SessionManager(base_dir=str(session_dir))

    @app.get("/api/v1/system/status")
    async def status():
        llm = resolve_llm_env()
        return {
            "backend": {"status": "online"},
            "llm": {
                "status": "configured",
                "model": llm["model"],
                "binding": llm["binding"],
                "source": llm["source"],
            },
            "embeddings": {"status": "not_configured"},
            "tts": {"status": "not_configured"},
        }

    @app.websocket("/api/v1/chat")
    async def chat(websocket: WebSocket):
        await websocket.accept()
        while True:
            try:
                payload = await websocket.receive_json()
            except Exception:
                break

            message = str(payload.get("message") or "").strip()
            if not message:
                await websocket.send_json(
                    {"type": "error", "message": "Message is required"}
                )
                continue

            session_id = payload.get("session_id")
            history = payload.get("history")
            kb_name = payload.get("kb_name", "")
            enable_rag = bool(payload.get("enable_rag", False))
            enable_web_search = bool(payload.get("enable_web_search", False))

            if session_id:
                session = session_manager.get_session(session_id)
                if session is None:
                    session = session_manager.create_session(
                        title=message[:50],
                        settings={
                            "kb_name": kb_name,
                            "enable_rag": enable_rag,
                            "enable_web_search": enable_web_search,
                        },
                    )
                    session_id = session["session_id"]
            else:
                session = session_manager.create_session(
                    title=message[:50],
                    settings={
                        "kb_name": kb_name,
                        "enable_rag": enable_rag,
                        "enable_web_search": enable_web_search,
                    },
                )
                session_id = session["session_id"]

            await websocket.send_json({"type": "session", "session_id": session_id})
            await websocket.send_json(
                {
                    "type": "status",
                    "stage": "generating",
                    "message": "Generating response...",
                }
            )

            if history is None:
                history = [
                    {"role": item["role"], "content": item["content"]}
                    for item in session.get("messages", [])
                ]

            session_manager.add_message(
                session_id=session_id,
                role="user",
                content=message,
            )

            agent = ChatAgent(language="zh", config={})

            try:
                stream_generator = await agent.process(
                    message=message,
                    history=history,
                    kb_name=kb_name,
                    enable_rag=enable_rag,
                    enable_web_search=enable_web_search,
                    stream=True,
                )
                full_response = ""
                sources = {"rag": [], "web": []}
                async for event in stream_generator:
                    if event["type"] == "chunk":
                        full_response += event["content"]
                        await websocket.send_json(
                            {"type": "stream", "content": event["content"]}
                        )
                    elif event["type"] == "complete":
                        sources = event.get("sources", {"rag": [], "web": []})

                session_manager.add_message(
                    session_id=session_id,
                    role="assistant",
                    content=full_response,
                    sources=sources,
                )
                await websocket.send_json({"type": "sources", **sources})
                await websocket.send_json(
                    {"type": "result", "content": full_response}
                )
            except Exception as exc:
                await websocket.send_json({"type": "error", "message": str(exc)})

    return app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8021)
    parser.add_argument(
        "--deeptutor-path",
        default=os.getenv("DEEPTUTOR_EXTERNAL_PATH", str(DEFAULT_DEEPTUTOR_PATH)),
    )
    args = parser.parse_args()

    repo_path = Path(args.deeptutor_path).expanduser()
    session_dir = PROJECT_ROOT / "artifacts" / "deeptutor-bridge"
    session_dir.mkdir(parents=True, exist_ok=True)

    app = create_app(repo_path, session_dir)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
