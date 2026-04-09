"""
Hermes External Adapter: true integration boundary with external Hermes agent.

This adapter represents the seam for the real Hermes external engine.
Currently implemented as a minimal shell that degrades safely if the external
engine is not configured or unavailable.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.review.contracts import FactPacket, ReviewBrief, ReviewPacketMetrics
from src.review.hermes_review_engine import HermesReviewEngine

logger = logging.getLogger(__name__)


class HermesExternalAdapter(HermesReviewEngine):
    """External Hermes agent integration adapter."""

    def __init__(self, endpoint: str | None = None):
        self._endpoint = endpoint

    @property
    def available(self) -> bool:
        """Return True if an external endpoint is configured.
        Note: True availability might also require a health check to the endpoint.
        """
        return bool(self._endpoint)

    async def review(
        self,
        brief: ReviewBrief,
        fact_packet_008: FactPacket | None = None,
        *,
        document_preview: str = '',
    ) -> FactPacket:
        """Execute review via external Hermes agent."""
        if not self.available:
            logger.info('[hermes_external] External endpoint not configured.')
            return self._degraded_packet(brief.review_id, 'External endpoint not configured')

        # TODO: Implement real HTTP/gRPC call to external Hermes agent here.
        # For now, since the actual external protocol is not yet mapped,
        # we honestly return 'not-implemented/unavailable'.
        logger.warning(
            '[hermes_external] External endpoint configured (%s), '
            'but actual integration is not yet implemented.',
            self._endpoint
        )
        return self._degraded_packet(
            brief.review_id,
            'External integration not fully implemented'
        )

    def _degraded_packet(self, review_id: str, reason: str) -> FactPacket:
        """Return a degraded packet denoting the failure or unavailability."""
        return FactPacket(
            review_id=review_id,
            engine='hermes_external',
            summary_metrics=ReviewPacketMetrics(),
            findings=[],
            overall_assessment=f'External Hermes Review unavailable: {reason}',
            raw_result={},
            produced_at=datetime.now(timezone.utc),
            error=reason,
            degraded=True,
        )
