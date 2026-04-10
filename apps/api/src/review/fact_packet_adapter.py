"""
008 Fact Packet Adapter: frozen 008-to-controller adapter.

Freeze boundary:
- adapter/bridge only
- do not expand with new business fields except migration/removal work


Design intent:
- Bridge between 008's native output format and the unified packet contract
- Does NOT change 008's internal behaviour — only adapts the output
- Preserves traceability to original issue IDs
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.review.contracts import FactPacket, FindingItem, ReviewPacketMetrics

logger = logging.getLogger(__name__)


class FactPacketAdapter:
    """Adapt 008 StructuredReviewResult dict into a FactPacket."""

    def adapt(self, review_id: str, result: dict) -> FactPacket:
        """Convert a StructuredReviewResult dict to a FactPacket."""
        logger.info('[fact_packet_adapter] Adapting 008 result for review %s', review_id)

        issues = result.get('issues', [])
        findings: list[FindingItem] = []

        for issue in issues:
            finding = FindingItem(
                id=issue.get('id', ''),
                title=issue.get('title', ''),
                severity=issue.get('severity', 'info'),
                category=self._infer_category(issue),
                layer=issue.get('layer', ''),
                evidence_status=self._map_evidence_status(issue),
                evidence_refs=self._extract_evidence_refs(issue),
                basis_refs=self._extract_basis_refs(issue),
                suggestion=self._join_recommendations(issue),
                summary=issue.get('summary', ''),
                finding_type=issue.get('findingType', ''),
                manual_review_needed=issue.get('manualReviewNeeded', False),
                confidence=issue.get('confidence', 'medium'),
                source_engine='008',
                raw_data=issue,
            )
            findings.append(finding)

        metrics = self._compute_metrics(findings)
        summary = result.get('summary', {})
        overall_conclusion = summary.get('overallConclusion', '') if isinstance(summary, dict) else ''

        packet = FactPacket(
            review_id=review_id,
            engine='008',
            summary_metrics=metrics,
            findings=findings,
            overall_assessment=overall_conclusion,
            raw_result=result,
            produced_at=datetime.now(timezone.utc),
            metadata={
                'worker_id': 'fact_packet_adapter',
                'module_id': 'structured_review_result',
            },
        )

        logger.info(
            '[fact_packet_adapter] 008 packet: %d findings (H=%d M=%d L=%d)',
            metrics.total_findings,
            metrics.high_severity,
            metrics.medium_severity,
            metrics.low_severity,
        )
        return packet

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _map_evidence_status(self, issue: dict) -> str:
        issue_kind = issue.get('issueKind', 'hard_defect')
        if issue_kind == 'visibility_gap':
            return 'visibility_gap'
        if issue_kind == 'evidence_gap':
            return 'evidence_gap'
        if issue.get('findingType') == 'engineering_inference':
            return 'inferred'
        return 'grounded'

    def _infer_category(self, issue: dict) -> str:
        finding_type = issue.get('findingType', '')
        if finding_type == 'visibility_gap':
            return 'visibility'
        layer = issue.get('layer', '')
        if layer == 'L1':
            return 'structure'
        if layer == 'L2':
            return 'compliance'
        if layer == 'L3':
            return 'safety'
        return 'general'

    def _extract_evidence_refs(self, issue: dict) -> list[str]:
        refs: list[str] = []
        for span in issue.get('docEvidence', []):
            locator = span.get('locator', {})
            for key in ('blockId', 'tableId', 'attachmentId'):
                if key in locator:
                    refs.append(f'doc:{locator[key]}')
                    break
        return refs

    def _extract_basis_refs(self, issue: dict) -> list[str]:
        refs: list[str] = []
        for span in issue.get('policyEvidence', []):
            locator = span.get('locator', {})
            if 'clauseId' in locator:
                refs.append(f"policy:{locator['clauseId']}")
        return refs

    def _join_recommendations(self, issue: dict) -> str:
        recs = issue.get('recommendation', [])
        if isinstance(recs, list):
            return '; '.join(str(r) for r in recs)
        return str(recs or '')

    def _compute_metrics(self, findings: list[FindingItem]) -> ReviewPacketMetrics:
        return ReviewPacketMetrics(
            total_findings=len(findings),
            high_severity=sum(1 for f in findings if f.severity == 'high'),
            medium_severity=sum(1 for f in findings if f.severity == 'medium'),
            low_severity=sum(1 for f in findings if f.severity == 'low'),
            info_findings=sum(1 for f in findings if f.severity == 'info'),
            grounded_findings=sum(1 for f in findings if f.evidence_status == 'grounded'),
            evidence_gap_findings=sum(1 for f in findings if f.evidence_status == 'evidence_gap'),
            manual_review_needed=sum(1 for f in findings if f.manual_review_needed),
        )
