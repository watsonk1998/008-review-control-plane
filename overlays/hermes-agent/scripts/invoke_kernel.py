#!/usr/bin/env python3
"""
Hermes Kernel Invocation Shim — Shell-side subprocess wrapper.

This script runs as a SEPARATE PROCESS (subprocess) from the 008 control plane.
It bridges the gap between the 008 launcher and the upstream Hermes AIAgent:

  1. Reads a JSON payload from stdin (or --input-file)
  2. Optionally loads a system prompt from the overlay prompts directory
  3. Constructs a minimal AIAgent instance (quiet, limited iterations)
  4. Calls agent.chat(query)
  5. Outputs a structured JSON result to stdout

IMPORTANT:
  - This file lives in overlays/ (shell-side), NOT in external/hermes-agent/ (upstream)
  - It imports from upstream ONLY within its own subprocess context
  - The 008 main process never imports this file directly
  - Process isolation is the boundary mechanism

Usage (invoked by HermesKernelLauncher, not manually):
    echo '{"query":"...","model":"..."}' | python invoke_kernel.py --kernel-root /path/to/external/hermes-agent
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from pathlib import Path


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Hermes kernel invocation shim")
    parser.add_argument("--kernel-root", type=str, required=True,
                        help="Path to external/hermes-agent checkout")
    parser.add_argument("--overlay-root", type=str, default=None,
                        help="Path to overlays/hermes-agent")
    parser.add_argument("--input-file", type=str, default=None,
                        help="Read JSON input from file instead of stdin")
    parser.add_argument("--max-turns", type=int, default=2,
                        help="Maximum API iterations (default: 2)")
    parser.add_argument("--timeout-hint", type=int, default=120,
                        help="Advisory timeout in seconds (enforced by caller)")
    args = parser.parse_args()

    start_time = time.time()

    # ── Read input payload ──────────────────────────────────────────
    try:
        if args.input_file:
            with open(args.input_file, "r", encoding="utf-8") as f:
                payload = json.load(f)
        else:
            raw = sys.stdin.read()
            payload = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, IOError) as e:
        _emit_error("input_parse_error", str(e), start_time)
        return 1

    query = payload.get("query", "")
    model = payload.get("model", "")
    api_key = payload.get("api_key", "")
    base_url = payload.get("base_url", "")
    review_id = payload.get("review_id", "local-kernel-invocation")
    system_prompt_override = payload.get("system_prompt", None)

    if not query:
        _emit_error("missing_query", "payload.query is required", start_time)
        return 1

    # ── Resolve overlay system prompt ───────────────────────────────
    system_prompt = system_prompt_override
    if not system_prompt and args.overlay_root:
        prompt_path = Path(args.overlay_root) / "prompts" / "hermes_review_system_prompt.md"
        if prompt_path.is_file():
            # Read and strip the header comment lines (lines starting with #)
            raw_prompt = prompt_path.read_text(encoding="utf-8")
            lines = raw_prompt.splitlines()
            content_lines = []
            in_header = True
            for line in lines:
                if in_header and line.strip().startswith("#"):
                    continue
                in_header = False
                content_lines.append(line)
            system_prompt = "\n".join(content_lines).strip()

    # ── Prepare upstream import ─────────────────────────────────────
    kernel_root = Path(args.kernel_root).resolve()
    if not kernel_root.is_dir():
        _emit_error("kernel_not_found", f"kernel root does not exist: {kernel_root}", start_time)
        return 1

    # Add kernel root to sys.path so we can import run_agent
    sys.path.insert(0, str(kernel_root))

    # Suppress noisy startup output from upstream
    os.environ["HERMES_QUIET"] = "1"

    try:
        from run_agent import AIAgent
    except ImportError as e:
        _emit_error("import_error", f"Cannot import AIAgent from kernel: {e}", start_time)
        return 1

    # ── Construct and run the agent ─────────────────────────────────
    try:
        agent_kwargs = {
            "max_iterations": args.max_turns,
            "quiet_mode": True,
            "verbose_logging": False,
            "enabled_toolsets": [],        # No tools for minimal execution
            "disabled_toolsets": ["terminal", "web", "creative", "vision"],
            "save_trajectories": False,
            "skip_context_files": True,    # Don't load repo context
            "skip_memory": True,           # Don't load memory
        }

        if model:
            agent_kwargs["model"] = model
        if api_key:
            agent_kwargs["api_key"] = api_key
        if base_url:
            agent_kwargs["base_url"] = base_url
        if payload.get("provider"):
            agent_kwargs["provider"] = payload.get("provider")
        if system_prompt:
            agent_kwargs["ephemeral_system_prompt"] = system_prompt

        agent = AIAgent(**agent_kwargs)
        result = agent.run_conversation(query)

        elapsed = time.time() - start_time

        output = {
            "success": True,
            "review_id": review_id,
            "source": "local_kernel",
            "response": result.get("final_response", ""),
            "completed": result.get("completed", False),
            "api_calls": result.get("api_calls", 0),
            "model": result.get("model", model),
            "provider": result.get("provider", ""),
            "input_tokens": result.get("input_tokens", 0),
            "output_tokens": result.get("output_tokens", 0),
            "elapsed_seconds": round(elapsed, 2),
            "overlay_prompt_loaded": system_prompt is not None,
            "error": None,
        }

    except Exception as e:
        elapsed = time.time() - start_time
        output = {
            "success": False,
            "review_id": review_id,
            "source": "local_kernel",
            "response": "",
            "completed": False,
            "api_calls": 0,
            "model": model,
            "provider": payload.get("provider", ""),
            "input_tokens": 0,
            "output_tokens": 0,
            "elapsed_seconds": round(elapsed, 2),
            "overlay_prompt_loaded": system_prompt is not None,
            "error": f"{type(e).__name__}: {e}",
            "traceback": traceback.format_exc(),
        }

    # ── Emit result as single-line JSON to stdout ───────────────────
    # Use a delimiter so the launcher can reliably find the JSON
    # even if upstream code prints other things to stdout
    marker = "<<<HERMES_KERNEL_RESULT>>>"
    print(marker, flush=True)
    print(json.dumps(output, ensure_ascii=False), flush=True)
    print(marker, flush=True)

    return 0 if output["success"] else 1


def _emit_error(code: str, message: str, start_time: float):
    """Emit a structured error JSON and exit."""
    marker = "<<<HERMES_KERNEL_RESULT>>>"
    output = {
        "success": False,
        "review_id": "",
        "source": "local_kernel",
        "response": "",
        "completed": False,
        "api_calls": 0,
        "model": "",
        "provider": "",
        "input_tokens": 0,
        "output_tokens": 0,
        "elapsed_seconds": round(time.time() - start_time, 2),
        "overlay_prompt_loaded": False,
        "error": f"{code}: {message}",
    }
    print(marker, flush=True)
    print(json.dumps(output, ensure_ascii=False), flush=True)
    print(marker, flush=True)


if __name__ == "__main__":
    sys.exit(main() or 0)
