"""
Hermes backend router for HermesController-first structured review.

Status:
- official backend router

Freeze boundary:
- backend routing only
- do not add controller semantics or final-output ownership here

Do not extend:
- no template-selection policy
- no runtime orchestration logic
- no second result protocol

Canonical path:
- HermesController owns orchestration
- HermesRouterAdapter chooses between external Hermes and local fallback backends
"""
from __future__ import annotations

import logging
from typing import Any

from src.review.contracts import FactPacket, ReviewBrief
from src.review.hermes_review_engine import HermesReviewEngine
from src.adapters.hermes_local_kernel_adapter import HermesLocalKernelAdapter
from src.adapters.hermes_external_adapter import HermesExternalAdapter
from src.adapters.hermes_llm_adapter import HermesLLMAdapter

logger = logging.getLogger(__name__)

class HermesRouterAdapter(HermesReviewEngine):
    """Facade that dynamically routes to local_kernel (default), external Hermes, or falls back to LLM."""

    def __init__(
        self,
        local_kernel_adapter: HermesLocalKernelAdapter | None,
        external_adapter: HermesExternalAdapter | None,
        llm_adapter: HermesLLMAdapter | None,
    ):
        self._local_kernel = local_kernel_adapter
        self._external = external_adapter
        self._llm = llm_adapter

    @property
    def available(self) -> bool:
        return (self._local_kernel and self._local_kernel.available) or \
               (self._external and self._external.available) or \
               (self._llm and self._llm.available)

    async def health_check(self) -> dict[str, Any]:
        """Return composite health of the available engines."""
        if self._local_kernel and self._local_kernel.available:
            local_health = await self._local_kernel.health_check()
            if local_health.get('available'):
                return local_health

        if self._external and self._external.available:
            ext_health = await self._external.health_check()
            # If external is healthy, return it as active mode
            if ext_health.get('available'):
                return ext_health

        if self._llm and self._llm.available:
            llm_health = await self._llm.health_check()
            if llm_health.get('available'):
                return llm_health

        return {'available': False, 'mode': 'not_configured', 'detail': 'No Hermes engine available'}

    async def review(
        self,
        brief: ReviewBrief,
        fact_packet_008: FactPacket | None = None,
        *,
        document_preview: str = '',
        governed_support_packet: dict[str, Any] | None = None,
    ) -> FactPacket:
        """Route to local_kernel if healthy, fallback to external, then fallback to LLM."""
        
        # 1. Local Kernel (Default Main Chain)
        if self._local_kernel and self._local_kernel.available:
            logger.info('[hermes_router] Routing to local_kernel adapter')
            packet = await self._local_kernel.review(
                brief=brief, fact_packet_008=fact_packet_008, document_preview=document_preview,
                governed_support_packet=governed_support_packet
            )
            if not packet.degraded:
                return packet
            logger.warning('[hermes_router] local_kernel returned degraded packet. Falling back.')

        # 2. External Kernel
        if self._external and self._external.available:
            ext_health = await self._external.health_check()
            if ext_health.get('available'):
                logger.info('[hermes_router] Routing to external Hermes adapter')
                packet = await self._external.review(
                    brief=brief, fact_packet_008=fact_packet_008, document_preview=document_preview,
                    governed_support_packet=governed_support_packet
                )
                if not packet.degraded:
                    return packet
                logger.warning('[hermes_router] External adapter returned degraded packet. Falling back.')
            else:
                logger.warning('[hermes_router] External adapter unhealthy. Falling back.')
                
        # 3. LLM Fallback
        if adapter := self._llm:
            logger.info('[hermes_router] Routing to LLM fallback adapter')
            return await adapter.review(
                brief=brief,
                fact_packet_008=fact_packet_008,
                document_preview=document_preview,
                governed_support_packet=governed_support_packet,
            )
            
        # If neither is available or both failed
        if self._external:
            return self._external._degraded_packet(brief.review_id, 'No Hermes engines available')
        return FactPacket(review_id=brief.review_id, engine='hermes', summary_metrics=None, findings=[], overall_assessment='Failed', raw_result={}, produced_at=None, error='No Hermes engines available', degraded=True)
