from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.review.contracts import FactPacket, FinalReportPacket, ReviewPacketMetrics
from src.review.final_report_merger import FinalReportMerger


class HermesReviewAssembler:
    """Official final output entrypoint for HermesController-first structured review.

    The assembler owns the external final result protocol exposed by controller/runtime.
    FinalReportMerger is only an internal helper used here for packet fusion.
    """

    def __init__(self):
        self.merger = FinalReportMerger()

    def assemble(
        self,
        *,
        brief,
        support_packet_008: FactPacket | None,
        hermes_review_packets: list[FactPacket],
        support_result_008: dict[str, Any] | None,
        agent_results: list[dict[str, Any]],
    ) -> tuple[dict[str, Any], FinalReportPacket | None]:
        if support_packet_008 is None:
            payload = dict(support_result_008 or {})
            payload['hermesController'] = {
                'enabled': True,
                'agentResults': agent_results,
                'finalReportReady': False,
            }
            return payload, None
        merged_hermes_main_review = self._merge_hermes_review_outcomes(support_packet_008.review_id, hermes_review_packets)
        support_packet_008, merged_hermes_main_review = self._apply_support_confidence_adjustments(
            support_packet_008=support_packet_008,
            hermes_review_packet=merged_hermes_main_review,
        )
        support_packet_008, merged_hermes_main_review = self._resolve_conflicts_and_gaps(
            support_packet_008=support_packet_008,
            hermes_review_packet=merged_hermes_main_review,
        )
        final_packet = self._build_final_decision_packet(
            brief=brief,
            support_packet_008=support_packet_008,
            hermes_review_packet=merged_hermes_main_review,
        )
        final_packet.metadata = {
            **final_packet.metadata,
            'assembler': 'hermes_review_assembler',
            'supplemental_packet_count': len(hermes_review_packets),
            'decision_owner': 'hermes',
            'support_owner': 'structured_review_capability_facade',
            'final_output_entrypoint': 'hermes_review_assembler',
        }
        payload = dict(support_result_008 or support_packet_008.raw_result or {})
        payload['hermesController'] = {
            'enabled': True,
            'selectedAgents': [result.get('agent_id') for result in agent_results],
            'agentResults': agent_results,
            'finalReportReady': True,
            'supplementalPacketCount': len(hermes_review_packets),
            'mainReviewOwnedBy': 'hermes',
            'decisionOwner': 'hermes',
            'supportOwner': 'structured_review_capability_facade',
        }
        payload['traceability'] = final_packet.traceability
        payload['finalReportMarkdown'] = final_packet.report_markdown
        payload['finalReportPacket'] = final_packet.model_dump(mode='json')
        payload['finalAnswer'] = final_packet.report_markdown
        return payload, final_packet

    def _merge_hermes_review_outcomes(self, review_id: str, packets: list[FactPacket]) -> FactPacket | None:
        if not packets:
            return None
        findings = []
        metadata_packets = []
        for packet in packets:
            findings.extend(packet.findings)
            metadata_packets.append({
                'metadata': packet.metadata,
                'overall_assessment': packet.overall_assessment,
            })
        metrics = ReviewPacketMetrics(
            total_findings=len(findings),
            high_severity=sum(1 for item in findings if item.severity == 'high'),
            medium_severity=sum(1 for item in findings if item.severity == 'medium'),
            low_severity=sum(1 for item in findings if item.severity == 'low'),
            info_findings=sum(1 for item in findings if item.severity == 'info'),
            grounded_findings=sum(1 for item in findings if item.evidence_status == 'grounded'),
            evidence_gap_findings=sum(1 for item in findings if item.evidence_status == 'evidence_gap'),
            manual_review_needed=sum(1 for item in findings if item.manual_review_needed),
        )
        return FactPacket(
            review_id=review_id,
            engine='hermes',
            summary_metrics=metrics,
            findings=findings,
            overall_assessment='；'.join(packet.overall_assessment for packet in packets if packet.overall_assessment),
            produced_at=datetime.now(timezone.utc),
            metadata={
                'worker_id': 'supplemental_packet_merge',
                'source_packets': metadata_packets,
                'ownership': 'hermes_main_review',
            },
        )

    def _apply_support_confidence_adjustments(
        self,
        *,
        support_packet_008: FactPacket,
        hermes_review_packet: FactPacket | None,
    ) -> tuple[FactPacket, FactPacket | None]:
        if hermes_review_packet is None:
            return support_packet_008, hermes_review_packet
        adjusted_support = support_packet_008.model_copy(deep=True)
        hermes_titles = {finding.title for finding in hermes_review_packet.findings}
        for finding in adjusted_support.findings:
            if finding.title in hermes_titles:
                finding.raw_data = {**finding.raw_data, 'hermes_decision_signal': 'corroborated'}
        return adjusted_support, hermes_review_packet

    def _resolve_conflicts_and_gaps(
        self,
        *,
        support_packet_008: FactPacket,
        hermes_review_packet: FactPacket | None,
    ) -> tuple[FactPacket, FactPacket | None]:
        if hermes_review_packet is None:
            return support_packet_008, hermes_review_packet
        adjusted_hermes = hermes_review_packet.model_copy(deep=True)
        support_titles = {finding.title for finding in support_packet_008.findings}
        for finding in adjusted_hermes.findings:
            if finding.evidence_status in {'evidence_gap', 'visibility_gap'}:
                finding.raw_data = {**finding.raw_data, 'decision_action': 'degraded_by_support_evidence_gap'}
            elif finding.title not in support_titles:
                finding.raw_data = {**finding.raw_data, 'decision_action': 'supplement_from_support_gap_scan'}
        return support_packet_008, adjusted_hermes

    def _build_final_decision_packet(
        self,
        *,
        brief,
        support_packet_008: FactPacket,
        hermes_review_packet: FactPacket | None,
    ) -> FinalReportPacket:
        packet = self.merger.fuse(
            brief=brief,
            packet_008=support_packet_008,
            packet_hermes=hermes_review_packet,
        )
        self._annotate_final_decision_findings(
            packet,
            support_packet_008=support_packet_008,
            hermes_review_packet=hermes_review_packet,
        )
        return packet

    def _annotate_final_decision_findings(
        self,
        packet: FinalReportPacket,
        *,
        support_packet_008: FactPacket,
        hermes_review_packet: FactPacket | None,
    ) -> None:
        support_modules = list(support_packet_008.metadata.get('review_modules') or [])
        hermes_modules = list((hermes_review_packet.metadata if hermes_review_packet else {}).get('review_modules') or [])

        for finding in packet.key_findings:
            module_name = self._prefer_single_module(
                finding.raw_data.get('review_modules'),
                support_modules,
            )
            finding.raw_data = {
                **finding.raw_data,
                'decision_role': 'key_finding',
                'decision_owner': 'hermes',
                'ownership': finding.raw_data.get('ownership', support_packet_008.metadata.get('ownership', 'support_material')),
                'source_template_id': finding.raw_data.get('template_id') or support_packet_008.metadata.get('template_id'),
                'review_modules': finding.raw_data.get('review_modules') or support_modules,
                **({'module_name': module_name} if module_name else {}),
            }

        for finding in packet.supplemental_findings:
            module_name = self._prefer_single_module(
                finding.raw_data.get('review_modules'),
                hermes_modules,
            )
            finding.raw_data = {
                **finding.raw_data,
                'decision_role': 'supplemental_finding',
                'decision_owner': 'hermes',
                'ownership': finding.raw_data.get('ownership', 'hermes_main_review'),
                'source_template_id': finding.raw_data.get('template_id') or (hermes_review_packet.metadata.get('template_id') if hermes_review_packet else None),
                'review_modules': finding.raw_data.get('review_modules') or hermes_modules,
                **({'module_name': module_name} if module_name else {}),
            }

        final_index = {finding.id: finding for finding in packet.key_findings + packet.supplemental_findings}
        for finding in packet.all_findings:
            source = final_index.get(finding.id)
            if source is not None:
                finding.raw_data = {**source.raw_data}
            else:
                finding.raw_data = {
                    **finding.raw_data,
                    'decision_role': 'all_finding',
                    'decision_owner': 'hermes',
                }

    def _prefer_single_module(self, *module_lists: Any) -> str | None:
        for modules in module_lists:
            if isinstance(modules, list) and len(modules) == 1 and modules[0]:
                return str(modules[0])
        return None
