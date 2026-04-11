"""
Hermes Kernel Launcher.

Status:
- smoke / non-default
- not enabled in active runtime

Responsible for managing the execution environment, lifecycle, and
overlay injections (skills, memory, config) for the isolated external/hermes-agent submodule.

Modes:
- dry_run: inspect paths, resolve overlays, generate launch plan — never spawn process
- smoke:   attempt minimal startup logic, return controlled degraded result
           if full kernel execution is not yet available
"""
from __future__ import annotations

import logging
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
    """Describes what the launcher *would* do if fully enabled."""

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
    """Controlled result object from a smoke invocation."""

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
    It exists to:
    1. Let developers verify that the kernel boundary is locatable.
    2. Let developers verify that the overlay directory structure is valid.
    3. Provide a minimal smoke execution contract that can be extended
       as the local kernel integration matures.
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
        """Attempt minimal startup logic.

        Does NOT spawn a real kernel subprocess yet.
        Returns a controlled SmokeResult indicating current capability.
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
            message="Smoke path OK: kernel located, overlay resolved, payload echoed. Full execution not yet implemented.",
            plan=plan,
            payload_echo=echo,
        )

    # ── Future interfaces (skeleton) ────────────────────────────────

    async def start(self) -> None:
        """
        Prepare environment and spawn the kernel process.
        TODO: Implement subprocess start, passing overlay boundaries as ENV or CLI args.
        """
        logger.info("[hermes_launcher] start() called (skeleton implementation).")
        pass

    async def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Send a payload to the kernel and await the response.
        TODO: Implement communication (e.g. process pipes or a local domain socket/port).
        """
        logger.warning("[hermes_launcher] invoke() is a skeleton placeholder.")
        return {}

    async def stop(self) -> None:
        """
        Gracefully terminate the sidecar/subprocess.
        """
        logger.info("[hermes_launcher] stop() called (skeleton implementation).")
        pass
