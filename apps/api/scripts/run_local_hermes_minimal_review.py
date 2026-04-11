#!/usr/bin/env python3
"""
Explicit entry point for the Hermes Local Kernel Minimal Review validation.

Usage:
    export DASHSCOPE_API_KEY="sk-..."
    python apps/api/scripts/run_local_hermes_minimal_review.py

This script explicitly instantiates the Local Kernel Adapter and Launcher,
forces the adapter into an 'enabled' state, and issues a minimal real review
request to prove the subprocess / overlay integration works.

It does NOT modify the main production wiring and keeps the local kernel path non-default.
"""

import sys
import asyncio
import argparse
import logging
from pathlib import Path

# Adjust sys.path so we can import from src without problems
api_root = Path(__file__).parent.parent.resolve()
if str(api_root) not in sys.path:
    sys.path.insert(0, str(api_root))

from src.adapters.hermes_kernel_launcher import HermesKernelLauncher
from src.adapters.hermes_local_kernel_adapter import HermesLocalKernelAdapter
from src.review.contracts import ReviewBrief

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def run_minimal_review(timeout: int):
    # ── 1. Locate paths ──
    repo_root = api_root.parent.parent
    kernel_path = repo_root / "external" / "hermes-agent"
    overlays_path = repo_root / "overlays" / "hermes-agent"

    print("============================================================")
    print("  Hermes Local Kernel — Minimal Review Path")
    print("============================================================")
    print(f"Kernel path:   {kernel_path}")
    print(f"Overlays path: {overlays_path}")
    print("-" * 60)

    # ── 2. Create the components ──
    launcher = HermesKernelLauncher(kernel_path=kernel_path, overlays_path=overlays_path)
    adapter = HermesLocalKernelAdapter(launcher=launcher)

    # Note: the adapter is intentionally non-default!
    # To run a real review through it, we must force the feature flag:
    adapter._is_enabled = True

    plan = launcher.inspect()
    if not plan.viable:
        print(f"❌ Kernel configuration is not viable: {plan.errors}")
        sys.exit(1)

    print("✅ Configuration is viable. Initiating minimal realistic execution...\n")

    # ── 3. Prepare the input contract ──
    brief = ReviewBrief(
        review_id="minimal-review-001",
        review_object_type="construction_scheme",
    )

    document_preview = "1.1 The power outage plan indicates disconnecting line A. However, the temporary ground wire is scheduled to be removed 2 hours before the line is re-energized."

    # ── 4. Execute the minimal real review ──
    try:
        packet = await asyncio.wait_for(
            adapter.review(brief, document_preview=document_preview),
            timeout=(timeout + 5) # add some buffer outside the subprocess timeout
        )
    except asyncio.TimeoutError:
        print(f"❌ Timed out waiting for adapter review ({timeout + 5}s)")
        sys.exit(1)

    print("-" * 60)
    print("  Minimal Review Result received")
    print("-" * 60)

    print(f"Success:      {not packet.degraded}")
    if packet.error:
        print(f"Error Status: {packet.error}")
        
    print(f"Assessment:   {packet.overall_assessment}")
    
    md = packet.metadata or {}
    print("\nMetadata Highlights:")
    print(f" - Source: {md.get('source', 'unknown')}")
    print(f" - API Calls: {md.get('api_calls', 0)}")
    print(f" - Elapsed: {md.get('elapsed_seconds', 0)}s")
    print(f" - Prompt Loaded from Overlay: {md.get('overlay_prompt_loaded', False)}")

    if packet.degraded:
        print("\n❌ Summary: Execution degraded/failed.")
        sys.exit(1)
    else:
        print("\n✅ Summary: Minimal review executed successfully.")


def main():
    parser = argparse.ArgumentParser(description="Run minimal real execution of local kernel")
    parser.add_argument("--timeout", type=int, default=60, help="Timeout in seconds for execution")
    args = parser.parse_args()

    asyncio.run(run_minimal_review(args.timeout))


if __name__ == "__main__":
    main()
