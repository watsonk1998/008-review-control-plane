"""
Dual Review Orchestrator: coordinates 008 + Hermes pipeline.

Flow:
    1. adapt      → 008 result dict → FactPacket
    2. hermes     → ReviewBrief + 008 packet → Hermes FactPacket (with degradation)
    3. fuse       → both packets → FinalReportPacket
    4. enrich     → inject dual-review data into original result dict

This module does NOT import or modify StructuredReviewExecutor.
It receives already-completed 008 results and wraps them post-hoc.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable

from src.review.contracts import FactPacket, ReviewBrief
from src.review.fact_packet_adapter import FactPacketAdapter
from src.review.hermes_review_engine import HermesReviewEngine
from src.review.report_fusion import ReportFusionService

logger = logging.getLogger(__name__)


class DualReviewOrchestrator:
    """Orchestrate the 008 + Hermes dual-path review pipeline."""

    def __init__(self, *, hermes_engine: HermesReviewEngine):
        self.fact_packet_adapter = FactPacketAdapter()
        self.hermes_engine = hermes_engine
        self.report_fusion = ReportFusionService()

    async def orchestrate(
        self,
        *,
        review_brief: ReviewBrief,
        result_008: dict[str, Any],
        document_preview: str = '',
        emit: Callable[..., Any] | None = None,
        write_json_artifact: Callable[..., str] | None = None,
    ) -> dict[str, Any]:
        """Run the dual-path orchestration, returning enriched result dict."""
        rid = review_brief.review_id

        def _emit(stage, cap, status, msg):
            if emit:
                emit(stage, cap, status, msg)

        def _artifact(name, payload):
            if write_json_artifact:
                write_json_artifact(name, payload)

        # --- 1. Write review brief artifact ---
        _artifact('review-brief', review_brief.model_dump(mode='json'))
        _emit('task_compile', 'dual_review', 'completed', 'Review brief compiled')

        # --- 2. Adapt 008 result → FactPacket ---
        packet_008 = self.fact_packet_adapter.adapt(rid, result_008)
        _artifact('008-fact-packet', packet_008.model_dump(mode='json'))
        _emit(
            'fact_packet', '008_engine', 'completed',
            f'008 packet: {packet_008.summary_metrics.total_findings} findings',
        )

        # --- 3. Hermes second-path review ---
        packet_hermes: FactPacket | None = None
        if self.hermes_engine.available:
            _emit('hermes_review', 'hermes_engine', 'started', 'Hermes review started')
            try:
                packet_hermes = await self.hermes_engine.review(
                    brief=review_brief,
                    fact_packet_008=packet_008,
                    document_preview=document_preview,
                )
                _artifact('hermes-review-packet', packet_hermes.model_dump(mode='json'))
                if packet_hermes.degraded:
                    _emit('hermes_review', 'hermes_engine', 'failed',
                          f'Hermes degraded: {packet_hermes.error}')
                else:
                    _emit('hermes_review', 'hermes_engine', 'completed',
                          f'Hermes: {packet_hermes.summary_metrics.total_findings} findings')
            except Exception as exc:
                logger.error('[dual_review] Hermes exception: %s', exc, exc_info=True)
                packet_hermes = FactPacket(
                    review_id=rid, engine='hermes',
                    error=str(exc), degraded=True,
                    produced_at=datetime.now(timezone.utc),
                )
                _emit('hermes_review', 'hermes_engine', 'failed', f'Hermes exception: {exc}')
        else:
            logger.info('[dual_review] Hermes not configured, skipping')
            _emit('hermes_review', 'hermes_engine', 'info', 'Hermes not configured, skipping')

        # --- 4. Fusion ---
        _emit('fusion', 'report_fusion', 'started', 'Report fusion started')
        final = self.report_fusion.fuse(
            brief=review_brief,
            packet_008=packet_008,
            packet_hermes=packet_hermes,
        )
        _artifact('final-report-packet', final.model_dump(mode='json'))
        _emit(
            'fusion', 'report_fusion', 'completed',
            f'grade={final.final_grade} key={len(final.key_findings)} suppl={len(final.supplemental_findings)}',
        )

        # --- 5. Enrich original result dict ---
        enriched = dict(result_008)
        enriched['dualReview'] = {
            'enabled': True,
            'enginesUsed': final.engines_used,
            'finalGrade': final.final_grade,
            'executiveSummary': final.executive_summary,
            'hermesAvailable': self.hermes_engine.available,
            'hermesDegraded': packet_hermes.degraded if packet_hermes else True,
            'keyFindingsCount': len(final.key_findings),
            'supplementalFindingsCount': len(final.supplemental_findings),
            'fusionReportMarkdown': final.report_markdown,
        }
        if final.degradation_info:
            enriched['dualReview']['degradationInfo'] = final.degradation_info

        logger.info('[dual_review] Done: grade=%s engines=%s', final.final_grade, final.engines_used)
        return enriched
