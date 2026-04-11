"""
Local Kernel Adapter for Hermes Review.

Status:
- future / skeleton
- not enabled in active runtime

This adapter abstracts the communication with a local Hermes kernel 
instance (submodule) managed by the HermesKernelLauncher.
"""
from __future__ import annotations

import logging
from typing import Any

from src.review.contracts import FactPacket, ReviewBrief
from src.review.hermes_review_engine import HermesReviewEngine
from src.adapters.hermes_kernel_launcher import HermesKernelLauncher

logger = logging.getLogger(__name__)

class HermesLocalKernelAdapter(HermesReviewEngine):
    """Facade for executing reviews via a locally managed Hermes kernel process."""

    def __init__(self, launcher: HermesKernelLauncher | None = None):
        self._launcher = launcher
        self._is_enabled = False # Feature flag, implicitly false currently

    @property
    def available(self) -> bool:
        """Currently disabled by default as the kernel path is planned/skeleton mode."""
        return self._is_enabled and self._launcher is not None

    async def health_check(self) -> dict[str, Any]:
        if not self.available:
            return {
                'available': False, 
                'mode': 'local_kernel_available_not_enabled', 
                'detail': 'Local kernel adapter skeleton exists but is not activated.'
            }
        
        # TODO: Implement actual sidecar/subprocess health probing via launcher
        return {
            'available': False,
            'mode': 'not_implemented',
            'detail': 'Health check for local kernel not yet implemented'
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
        """
        if not self.available:
            return FactPacket(
                review_id=brief.review_id,
                engine="hermes",
                overall_assessment="Local Kernel Adapter is not enabled.",
                degraded=True,
                error="not_enabled"
            )
            
        logger.info(f"[hermes_local_kernel] Initiating review for {brief.review_id} via local kernel")
        # TODO: Implement request serialization and exchange protocol utilizing self._launcher
        
        return FactPacket(
                review_id=brief.review_id,
                engine="hermes",
                overall_assessment="Method not implemented in skeleton adapter.",
                degraded=True,
                error="not_implemented"
        )
