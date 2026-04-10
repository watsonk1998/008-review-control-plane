"""
Hermes Review Engine Abstract Interface.

Defines the boundary contract for Hermes second-path review, allowing the
orchestrator to seamlessly switch between local LLM-based approximation
and the true external Hermes agent.
"""

from __future__ import annotations

import abc
from typing import Any

from src.review.contracts import FactPacket, ReviewBrief


class HermesReviewEngine(abc.ABC):
    """Abstract base class for Hermes review engines."""

    @property
    @abc.abstractmethod
    def available(self) -> bool:
        """Return True if the engine is configured and fundamentally available."""
        pass

    @abc.abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Check health status. Should return detailed state like not_configured, available, etc."""
        pass

    @abc.abstractmethod
    async def review(
        self,
        brief: ReviewBrief,
        fact_packet_008: FactPacket | None = None,
        *,
        document_preview: str = '',
    ) -> FactPacket:
        """Execute Hermes second-path review.

        Returns a FactPacket with engine='hermes'.
        If the engine is unavailable, degraded, or fails, it must return a
        degraded packet (degraded=True, with error set).
        """
        pass
