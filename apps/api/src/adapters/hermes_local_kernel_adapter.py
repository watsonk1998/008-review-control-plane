"""
Local Kernel Adapter for Hermes Review.

Status:
- minimal real execution available
- non-default / explicit-only
- NOT wired into production runtime — MUST NOT appear in main_dependencies.py

This adapter abstracts the communication with a local Hermes kernel
instance (submodule) managed by the HermesKernelLauncher.

Current capabilities:
- smoke mode: exercises the launcher dry-run + smoke path to validate
  kernel location, overlay resolution, and controlled result generation.
- real execution mode: invokes a subprocess via the launcher's invoke()
  method to perform a minimal real review through the local kernel.
  Returns structured FactPacket mapped from subprocess output.

Capability boundary:
- Minimal execution only — not a full production-grade review path.
- Non-default: adapter._is_enabled must be explicitly set to True.
- Allows graceful degradation and controlled failure.
"""
from __future__ import annotations

import json
import logging
import os
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
    - the explicit minimal review script (apps/api/scripts/run_local_hermes_minimal_review.py)
    - direct programmatic construction in tests

    It must NOT appear in main_dependencies.get_hermes_engine().
    """

    def __init__(self, launcher: HermesKernelLauncher | None = None):
        self._launcher = launcher
        self._is_enabled = False  # Feature flag, implicitly false — non-default

    @property
    def available(self) -> bool:
        """Non-default: disabled unless adapter._is_enabled is explicitly set to True."""
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

        When not enabled, returns a controlled degraded packet.
        When enabled, invokes the launcher subprocess for minimal real execution.
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
            "[hermes_local_kernel] Initiating review for %s via local kernel invoke",
            brief.review_id,
        )

        try:
            # Construct minimal input payload
            # Reading Dashscope API key from environment for now
            api_key = os.environ.get("DASHSCOPE_API_KEY", "")
            if not api_key:
                logger.warning("DASHSCOPE_API_KEY not found in environment")

            # Extract context from brief or fact_packet if available
            context_excerpt = document_preview
            if not context_excerpt and fact_packet_008 and fact_packet_008.findings:
                context_excerpt = f"We have {len(fact_packet_008.findings)} previous findings from 008 engine."

            # Construct the query matching typical objective
            prompt = (
                f"Review ID: {brief.review_id}\n"
                f"Document Type: {brief.review_object_type}\n\n"
                f"Please review the following document excerpt and provide a JSON response:\n"
                f"{context_excerpt[:2000] if context_excerpt else 'No excerpt available.'}"
            )

            payload = {
                "review_id": brief.review_id,
                "query": prompt,
                "model": "qwen-max",
                "provider": "openai",
                "api_key": api_key,
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            }

            # Invoke launcher subprocess
            result = await self._launcher.invoke(payload)

            if not result.get("success"):
                return FactPacket(
                    review_id=brief.review_id,
                    engine="hermes",
                    overall_assessment=f"Local kernel execution failed: {result.get('error')}",
                    degraded=True,
                    error="local_kernel_error",
                    metadata=result,
                )

            response_json_str = result.get("response", "")
            
            # Try to parse the LLM output as JSON
            parsed_result = {}
            if response_json_str:
                # Strip markdown code blocks if the LLM wrapped it
                clean_json = response_json_str
                if clean_json.startswith("```json"):
                    clean_json = clean_json[7:]
                if clean_json.startswith("```"):
                    clean_json = clean_json[3:]
                clean_json = clean_json.strip()
                if clean_json.endswith("```"):
                    clean_json = clean_json[:-3].strip()

                try:
                    parsed_result = json.loads(clean_json)
                except json.JSONDecodeError as e:
                    logger.warning("Failed to parse LLM response as JSON: %s. Response: %s", e, response_json_str[:200])

            # Convert to FactPacket
            assessment = parsed_result.get("overall_assessment", "")
            if not assessment:
                assessment = "Review completed via minimal local kernel path (non-JSON response)."
                if response_json_str:
                    assessment += f"\nRaw response: {response_json_str[:500]}..."

            return FactPacket(
                review_id=brief.review_id,
                engine="hermes",
                summary_metrics=ReviewPacketMetrics(
                    total_findings=len(parsed_result.get("findings", [])),
                ),
                overall_assessment=assessment,
                degraded=False,
                error=None,
                metadata={
                    "source": "local_kernel_invoke",
                    "api_calls": result.get("api_calls"),
                    "elapsed_seconds": result.get("elapsed_seconds"),
                    "overlay_prompt_loaded": result.get("overlay_prompt_loaded"),
                    "parsed_top_risks": parsed_result.get("top_risks", []),
                    "parsed_grade": parsed_result.get("grade", ""),
                },
            )

        except Exception as e:
            logger.exception("Unexpected error during local kernel review")
            return FactPacket(
                review_id=brief.review_id,
                engine="hermes",
                overall_assessment=f"Unexpected error: {e}",
                degraded=True,
                error="unexpected_adapter_error",
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
                "This is a controlled diagnostic result — use review() with _is_enabled=True for real execution."
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
