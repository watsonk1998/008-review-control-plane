#!/usr/bin/env python3
"""
Local Hermes Kernel Smoke Path — Explicit Manual Trigger Only.

Status:
- smoke / diagnostic
- NOT part of the production runtime
- NOT auto-invoked by the main review chain

Purpose:
- Verify that `external/hermes-agent` can be located by the launcher
- Verify that the overlay directory structure is resolved correctly
- Exercise the launcher dry-run and smoke modes
- Produce a human-readable diagnostic report

Usage:
    python3 apps/api/scripts/run_local_hermes_smoke.py           # full smoke
    python3 apps/api/scripts/run_local_hermes_smoke.py --dry-run  # dry-run only
    python3 apps/api/scripts/run_local_hermes_smoke.py --json     # JSON output

Note:
    This script is intentionally self-contained. It imports only the
    launcher module (which has no heavy dependencies) and avoids importing
    the full production src.review / src.domain chain, which requires
    Python 3.10+ and pydantic v2.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path

# Resolve repo root
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]  # apps/api/scripts -> apps/api -> apps -> repo root
# Ensure src is importable
sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))

# Only import the launcher — it has no heavy deps (no pydantic, no domain model chain)
from src.adapters.hermes_kernel_launcher import HermesKernelLauncher

logger = logging.getLogger("hermes_smoke")

# ── Defaults ────────────────────────────────────────────────────────

DEFAULT_KERNEL_PATH = REPO_ROOT / "external" / "hermes-agent"
DEFAULT_OVERLAY_PATH = REPO_ROOT / "overlays" / "hermes-agent"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Run local Hermes kernel smoke path (non-production diagnostic)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Only inspect paths and generate a launch plan — skip smoke execution",
    )
    p.add_argument(
        "--kernel-path",
        type=Path,
        default=DEFAULT_KERNEL_PATH,
        help=f"Path to the Hermes kernel checkout (default: {DEFAULT_KERNEL_PATH})",
    )
    p.add_argument(
        "--overlay-path",
        type=Path,
        default=DEFAULT_OVERLAY_PATH,
        help=f"Path to the overlay root (default: {DEFAULT_OVERLAY_PATH})",
    )
    p.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    p.add_argument("--json", action="store_true", dest="json_output", help="Output as JSON")
    return p


def print_section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


async def run_dry_run(launcher: HermesKernelLauncher, *, json_output: bool) -> bool:
    plan = await launcher.dry_run()

    if json_output:
        print(json.dumps(asdict(plan), indent=2, default=str))
        return plan.viable

    print_section("Dry-Run: Launch Plan")
    print(f"  Kernel path:    {plan.kernel_path}")
    print(f"  Kernel exists:  {plan.kernel_exists}")
    print(f"  Overlay root:   {plan.overlay_root or '(not configured)'}")
    if plan.overlay_dirs_found:
        for name, found in plan.overlay_dirs_found.items():
            status = "✓" if found else "✗"
            print(f"    {status} {name}/")
    print(f"  Viable:         {plan.viable}")
    if plan.errors:
        print(f"  Errors:")
        for e in plan.errors:
            print(f"    ✗ {e}")
    if plan.warnings:
        print(f"  Warnings:")
        for w in plan.warnings:
            print(f"    ⚠ {w}")
    return plan.viable


async def run_smoke(launcher: HermesKernelLauncher, *, json_output: bool) -> bool:
    """Run the launcher smoke with a synthetic payload."""
    smoke_payload = {
        "review_id": "smoke-test-001",
        "mode": "smoke",
        "query": "Smoke test — local kernel path validation",
    }

    result = await launcher.smoke(payload=smoke_payload)

    if json_output:
        print(json.dumps(asdict(result), indent=2, default=str))
        return result.success

    print_section("Smoke Exercise Report")
    print(f"  Success:  {result.success}")
    print(f"  Mode:     {result.mode}")
    print(f"  Message:  {result.message}")

    if result.plan:
        print(f"\n  Launch plan:")
        print(f"    Kernel exists: {result.plan.kernel_exists}")
        print(f"    Viable:        {result.plan.viable}")
        if result.plan.overlay_dirs_found:
            print(f"    Overlays:")
            for name, found in result.plan.overlay_dirs_found.items():
                status = "✓" if found else "✗"
                print(f"      {status} {name}/")
        if result.plan.warnings:
            print(f"    Warnings:")
            for w in result.plan.warnings:
                print(f"      ⚠ {w}")

    if result.payload_echo:
        print(f"\n  Payload echo:")
        for k, v in result.payload_echo.items():
            print(f"    {k}: {v}")

    return result.success


async def main() -> int:
    args = build_parser().parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if not args.json_output:
        print("=" * 60)
        print("  Hermes Local Kernel — Smoke Path")
        print("  Mode: " + ("DRY-RUN" if args.dry_run else "SMOKE"))
        print("=" * 60)

    launcher = HermesKernelLauncher(
        kernel_path=args.kernel_path,
        overlays_path=args.overlay_path,
    )

    if args.dry_run:
        viable = await run_dry_run(launcher, json_output=args.json_output)
        if not args.json_output:
            print(f"\n{'PASS' if viable else 'FAIL'}: dry-run {'viable' if viable else 'not viable'}")
        return 0 if viable else 1

    # Full smoke path: dry-run first, then smoke
    viable = await run_dry_run(launcher, json_output=args.json_output)
    ok = await run_smoke(launcher, json_output=args.json_output)

    if not args.json_output:
        final = "PASS" if (viable and ok) else "PARTIAL" if viable or ok else "FAIL"
        print(f"\n{'=' * 60}")
        print(f"  Final: {final}")
        print(f"{'=' * 60}")

    return 0 if (viable and ok) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
