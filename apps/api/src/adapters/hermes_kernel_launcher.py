"""
Hermes Kernel Launcher.

Status:
- minimal real execution available
- non-default / explicit-only
- NOT wired into production runtime (main_dependencies.py)

Responsible for managing the execution environment, lifecycle, and
overlay injections (skills, memory, config) for the isolated external/hermes-agent submodule.

Modes:
- dry_run: inspect paths, resolve overlays, generate launch plan — never spawn process
- smoke:   validate kernel locatability and overlay resolution, return controlled
           SmokeResult without spawning a subprocess
- invoke:  spawn a real subprocess via invoke_kernel.py shim, send JSON payload
           via stdin, parse structured output — minimal real execution path

Current capability boundary:
- Minimal execution via subprocess (not full production-grade review)
- Graceful degradation on timeout, missing paths, or parse failure
- Process isolation via subprocess — no in-process kernel imports
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class LaunchMode(Enum):
    DRY_RUN = "dry_run"
    SMOKE = "smoke"


@dataclass
class LaunchPlan:
    """Describes the launch plan from path inspection (used by dry_run and smoke)."""

    kernel_path: str
    kernel_exists: bool
    overlay_root: str | None
    overlay_dirs_found: dict[str, bool] = field(default_factory=dict)
    mode: str = "dry_run"
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def viable(self) -> bool:
        return self.kernel_exists and len(self.errors) == 0


@dataclass
class SmokeResult:
    """Controlled result object from a smoke invocation (no subprocess spawned)."""

    success: bool
    mode: str = "smoke"
    message: str = ""
    plan: LaunchPlan | None = None
    payload_echo: dict[str, Any] = field(default_factory=dict)


# ── Overlay sub-directories expected under overlays/hermes-agent/ ──
EXPECTED_OVERLAY_SUBDIRS = ("skills", "memory", "config", "prompts")


class HermesKernelLauncher:
    """Manages the invocation of the local Hermes agent kernel.

    This launcher is intentionally NOT wired into the production runtime.
    Current capabilities:
    1. dry_run / inspect: verify kernel boundary and overlay structure.
    2. smoke: validate locatability without spawning a subprocess.
    3. invoke: spawn a real subprocess via invoke_kernel.py shim for
       minimal real execution (non-default, explicit-only).

    This launcher must NOT appear in main_dependencies.py.
    """

    def __init__(
        self,
        kernel_path: Path,
        overlays_path: Path | None = None,
    ):
        self.kernel_path = kernel_path
        self.overlays_path = overlays_path

    # ── Inspection ──────────────────────────────────────────────────

    def inspect(self) -> LaunchPlan:
        """Inspect kernel and overlay paths — pure read-only, no side effects."""
        errors: list[str] = []
        warnings: list[str] = []

        kernel_exists = self.kernel_path.is_dir()
        if not kernel_exists:
            errors.append(f"kernel_path does not exist: {self.kernel_path}")

        overlay_dirs: dict[str, bool] = {}
        overlay_root_str: str | None = None
        if self.overlays_path is not None:
            overlay_root_str = str(self.overlays_path)
            if not self.overlays_path.is_dir():
                warnings.append(f"overlay_root does not exist yet: {self.overlays_path}")
            else:
                for subdir in EXPECTED_OVERLAY_SUBDIRS:
                    overlay_dirs[subdir] = (self.overlays_path / subdir).is_dir()
        else:
            warnings.append("no overlay_root configured")

        return LaunchPlan(
            kernel_path=str(self.kernel_path),
            kernel_exists=kernel_exists,
            overlay_root=overlay_root_str,
            overlay_dirs_found=overlay_dirs,
            mode="dry_run",
            errors=errors,
            warnings=warnings,
        )

    # ── Dry-run ─────────────────────────────────────────────────────

    async def dry_run(self) -> LaunchPlan:
        """Generate a launch plan without spawning any process."""
        plan = self.inspect()
        logger.info(
            "[hermes_launcher] dry_run complete — viable=%s, errors=%d, warnings=%d",
            plan.viable,
            len(plan.errors),
            len(plan.warnings),
        )
        return plan

    # ── Smoke execution ─────────────────────────────────────────────

    async def smoke(self, payload: dict[str, Any] | None = None) -> SmokeResult:
        """Validate kernel locatability and overlay resolution.

        Does NOT spawn a subprocess — this is a pure diagnostic check.
        Use invoke() for real subprocess execution.
        """
        plan = self.inspect()
        plan.mode = "smoke"

        if not plan.viable:
            return SmokeResult(
                success=False,
                mode="smoke",
                message=f"Kernel not viable: {'; '.join(plan.errors)}",
                plan=plan,
            )

        # Check for run_agent.py as a marker of a valid upstream checkout
        run_agent = self.kernel_path / "run_agent.py"
        if not run_agent.is_file():
            plan.warnings.append("run_agent.py not found in kernel — submodule may not be initialized")

        # Echo payload to prove the round-trip contract works
        echo = payload or {}

        logger.info("[hermes_launcher] smoke complete — kernel located, overlay resolved")
        return SmokeResult(
            success=True,
            mode="smoke",
            message="Smoke path OK: kernel located, overlay resolved, payload echoed. Use invoke() for real subprocess execution.",
            plan=plan,
            payload_echo=echo,
        )

    # ── Lifecycle interfaces (skeleton) ─────────────────────────────

    async def start(self) -> None:
        """
        Prepare environment and spawn a persistent kernel process.
        Not yet implemented — use invoke() for per-request subprocess execution.
        """
        logger.info("[hermes_launcher] start() called (skeleton implementation).")
        pass

    async def invoke(self, payload: dict[str, Any], timeout_seconds: int = 120) -> dict[str, Any]:
        """
        Send a payload to the kernel via the invoke_kernel.py shim.
        """
        plan = self.inspect()
        if not plan.viable:
            return {
                "success": False,
                "review_id": payload.get("review_id", ""),
                "source": "local_kernel_launcher",
                "response": "",
                "error": f"Kernel not viable: {'; '.join(plan.errors)}",
            }
            
        if self.overlays_path is None:
            return {
                "success": False,
                "review_id": payload.get("review_id", ""),
                "source": "local_kernel_launcher",
                "response": "",
                "error": "No overlays_path configured",
            }

        shim_path = self.overlays_path / "scripts" / "invoke_kernel.py"
        if not shim_path.is_file():
            return {
                "success": False,
                "review_id": payload.get("review_id", ""),
                "source": "local_kernel_launcher",
                "response": "",
                "error": f"Invocation shim not found: {shim_path}",
            }

        cmd = [
            sys.executable,
            str(shim_path),
            "--kernel-root", str(self.kernel_path),
            "--overlay-root", str(self.overlays_path),
            "--timeout-hint", str(timeout_seconds),
        ]

        try:
            logger.info("[hermes_launcher] Invoking local kernel subprocess: %s", " ".join(cmd))
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            payload_bytes = json.dumps(payload).encode("utf-8")
            
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(input=payload_bytes),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return {
                    "success": False,
                    "review_id": payload.get("review_id", ""),
                    "source": "local_kernel_launcher",
                    "response": "",
                    "error": f"Subprocess timed out after {timeout_seconds}s",
                }

            stdout_str = stdout_bytes.decode("utf-8")
            stderr_str = stderr_bytes.decode("utf-8")
            
            if stderr_str:
                logger.debug("[hermes_launcher] Kernel stderr: %s", stderr_str)

            # Parse delimited JSON output from shim
            marker = "<<<HERMES_KERNEL_RESULT>>>"
            parts = stdout_str.split(marker)
            
            if len(parts) >= 3:
                json_str = parts[1].strip()
                try:
                    result = json.loads(json_str)
                    return result
                except json.JSONDecodeError as e:
                    return {
                        "success": False,
                        "review_id": payload.get("review_id", ""),
                        "source": "local_kernel_launcher",
                        "response": "",
                        "error": f"Failed to parse structured JSON from subprocess: {e}\nRaw output: {json_str[:500]}...",
                    }
            else:
                return {
                    "success": False,
                    "review_id": payload.get("review_id", ""),
                    "source": "local_kernel_launcher",
                    "response": "",
                    "error": f"No <<<HERMES_KERNEL_RESULT>>> markers found in output.\nStdout: {stdout_str}\nStderr: {stderr_str}",
                }

        except Exception as e:
            logger.exception("[hermes_launcher] Subprocess execution failed")
            return {
                "success": False,
                "review_id": payload.get("review_id", ""),
                "source": "local_kernel_launcher",
                "response": "",
                "error": f"Subprocess execution failed: {e}",
            }

    async def stop(self) -> None:
        """
        Gracefully terminate the sidecar/subprocess.
        """
        logger.info("[hermes_launcher] stop() called (skeleton implementation).")
        pass
