"""
Local Kernel Adapter for Hermes Review.

Status:
- smoke / non-default
- not enabled in active runtime — MUST NOT be wired into main_dependencies.py

This adapter abstracts the communication with a local Hermes kernel
instance (submodule) managed by the HermesKernelLauncher.

Current capability:
- smoke mode: exercises the launcher dry-run + smoke path to validate
  kernel location, overlay resolution, and controlled result generation.
- Full kernel execution: not yet implemented.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.review.contracts import FactPacket, ReviewBrief, ReviewPacketMetrics
from src.review.hermes_review_engine import HermesReviewEngine
from src.adapters.hermes_kernel_launcher import (
    HermesKernelLauncher,
    LaunchMode,
    SmokeResult,
)

logger = logging.getLogger(__name__)


@dataclass
class LocalKernelSmokeReport:
    """Structured report from the local kernel smoke exercise."""

    adapter_enabled: bool
    launcher_available: bool
    smoke_result: SmokeResult | None = None
    review_packet: FactPacket | None = None
    errors: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class HermesLocalKernelAdapter(HermesReviewEngine):
    """Facade for executing reviews via a locally managed Hermes kernel process.

    WARNING: This adapter is NOT wired into the production runtime.
    It is only accessible through:
    - the explicit smoke script (apps/api/scripts/run_local_hermes_smoke.py)
    - direct programmatic construction in tests

    It must NOT appear in main_dependencies.get_hermes_engine().
    """

    def __init__(self, launcher: HermesKernelLauncher | None = None):
        self._launcher = launcher
        self._is_enabled = False  # Feature flag, implicitly false — non-default

    @property
    def available(self) -> bool:
        """Currently disabled by default as the kernel path is planned/skeleton mode."""
        return self._is_enabled and self._launcher is not None

    async def health_check(self) -> dict[str, Any]:
        if not self.available:
            return {
                'available': False,
                'mode': 'local_kernel_available_not_enabled',
                'detail': 'Local kernel adapter exists but is not activated in runtime.',
            }

        # TODO: Implement actual sidecar/subprocess health probing via launcher
        return {
            'available': False,
            'mode': 'not_implemented',
            'detail': 'Health check for local kernel not yet implemented',
        }

    async def review(
        self,
        brief: ReviewBrief,
        fact_packet_008: FactPacket | None = None,
        *,
        document_preview: str = '',
    ) -> FactPacket:
        """
        Execute review against the locally launched kernel.

        In smoke mode (default), returns a controlled degraded packet.
        Full kernel execution path is not yet implemented.
        """
        if not self.available:
            return FactPacket(
                review_id=brief.review_id,
                engine="hermes",
                overall_assessment="Local Kernel Adapter is not enabled.",
                degraded=True,
                error="not_enabled",
            )

        logger.info(
            "[hermes_local_kernel] Initiating review for %s via local kernel",
            brief.review_id,
        )
        # TODO: Implement request serialization and exchange protocol utilizing self._launcher
        return FactPacket(
            review_id=brief.review_id,
            engine="hermes",
            overall_assessment="Method not implemented in skeleton adapter.",
            degraded=True,
            error="not_implemented",
        )

    # ── Smoke-specific interface ────────────────────────────────────

    async def smoke_exercise(self, brief: ReviewBrief | None = None) -> LocalKernelSmokeReport:
        """Run the full smoke path without requiring the adapter to be 'enabled'.

        This is the primary entry point for the smoke script. It bypasses the
        `available` gate intentionally, because the purpose of smoke is to verify
        the path *could* work, not that it's production-enabled.

        Returns a structured LocalKernelSmokeReport.
        """
        errors: list[str] = []

        if self._launcher is None:
            errors.append("No HermesKernelLauncher provided")
            return LocalKernelSmokeReport(
                adapter_enabled=self._is_enabled,
                launcher_available=False,
                errors=errors,
            )

        # 1. Run launcher smoke
        smoke_result = await self._launcher.smoke(
            payload={
                "review_id": brief.review_id if brief else "smoke-test",
                "mode": "smoke",
            }
        )

        # 2. Generate a controlled review packet
        review_id = brief.review_id if brief else "smoke-test"
        review_packet = FactPacket(
            review_id=review_id,
            engine="hermes",
            summary_metrics=ReviewPacketMetrics(),
            overall_assessment=(
                "Smoke path executed successfully. "
                "This is a controlled result — full kernel execution is not yet implemented."
            ),
            degraded=True,
            error="smoke_only",
            metadata={
                "smoke": True,
                "kernel_viable": smoke_result.plan.viable if smoke_result.plan else False,
                "launcher_message": smoke_result.message,
            },
        )

        if not smoke_result.success:
            errors.append(f"Launcher smoke failed: {smoke_result.message}")

        return LocalKernelSmokeReport(
            adapter_enabled=self._is_enabled,
            launcher_available=True,
            smoke_result=smoke_result,
            review_packet=review_packet,
            errors=errors,
        )
