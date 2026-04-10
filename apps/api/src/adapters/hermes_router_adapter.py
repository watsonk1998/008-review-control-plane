"""
Hermes Router Adapter.

Dynamically routes Hermes review requests based on the health and availability
of the external Hermes endpoint vs the local LLM fallback.
"""
from __future__ import annotations

import logging
from typing import Any

from src.review.contracts import FactPacket, ReviewBrief
from src.review.hermes_review_engine import HermesReviewEngine
from src.adapters.hermes_external_adapter import HermesExternalAdapter
from src.adapters.hermes_llm_adapter import HermesLLMAdapter

logger = logging.getLogger(__name__)

class HermesRouterAdapter(HermesReviewEngine):
    """Facade that dynamically routes to external Hermes or falls back to LLM."""

    def __init__(self, external_adapter: HermesExternalAdapter, llm_adapter: HermesLLMAdapter):
        self._external = external_adapter
        self._llm = llm_adapter

    @property
    def available(self) -> bool:
        return self._external.available or self._llm.available

    async def health_check(self) -> dict[str, Any]:
        """Return composite health of the available engines."""
        if self._external.available:
            ext_health = await self._external.health_check()
            # If external is healthy, return it as active mode
            if ext_health.get('available'):
                return ext_health
            # Otherwise we still have a fallback
            if self._llm.available:
                llm_health = await self._llm.health_check()
                if llm_health.get('available'):
                    return {
                        'available': True,
                        'mode': 'llm_fallback_active',
                        'detail': f"External degraded ({ext_health.get('mode')}: {ext_health.get('detail')}), using LLM"
                    }
            return ext_health  # Both failed, return primary external failure
            
        if self._llm.available:
            return await self._llm.health_check()
            
        return {'available': False, 'mode': 'not_configured', 'detail': 'Neither external nor LLM Hermes configured'}

    async def review(
        self,
        brief: ReviewBrief,
        fact_packet_008: FactPacket | None = None,
        *,
        document_preview: str = '',
    ) -> FactPacket:
        """Route to external if healthy, fallback to LLM."""
        if self._external.available:
            ext_health = await self._external.health_check()
            if ext_health.get('available'):
                logger.info('[hermes_router] Routing to external Hermes adapter')
                packet = await self._external.review(
                    brief, fact_packet_008, document_preview=document_preview
                )
                if not packet.degraded:
                    return packet
                logger.warning('[hermes_router] External adapter returned degraded packet. Falling back.')
            else:
                logger.warning('[hermes_router] External adapter unhealthy. Falling back.')
                
        if self._llm.available:
            logger.info('[hermes_router] Routing to LLM fallback adapter')
            return await self._llm.review(
                brief, fact_packet_008, document_preview=document_preview
            )
            
        # If neither is available or both failed
        return self._external._degraded_packet(brief.review_id, 'No Hermes engines available')
