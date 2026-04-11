from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.review.contracts import FactPacket, FinalReportPacket, FindingItem, ReviewPacketMetrics, ReviewBrief
from src.review.final_report_merger import FinalReportMerger

_GRADE_LABELS = {
    'conditional_pass': '有条件通过',
    'needs_revision': '需要修改',
    'fail': '不通过',
}


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
        brief: ReviewBrief,
        support_packet_008: FactPacket,
        hermes_review_packet: FactPacket | None,
    ) -> FinalReportPacket:
        material = self.merger.prepare_decision_material(
            brief=brief,
            packet_008=support_packet_008,
            packet_hermes=hermes_review_packet,
        )

        all_findings = material['all_findings']
        key_findings = material['key_findings']
        supplemental_findings = material['supplemental_findings']

        # Hermes Assembler decides the final grade and risks
        top_risks = [item for item in all_findings if item.severity == 'high']
        final_grade = self._decide_grade(all_findings)
        executive_summary = self._decide_executive_summary(
            metrics=support_packet_008.summary_metrics,
            hermes_packet=hermes_review_packet,
            supplemental_count=len(supplemental_findings),
            grade=final_grade
        )

        report_markdown = self._render_markdown(
            doc_label=material['doc_label'],
            summary=executive_summary,
            top_risks=top_risks,
            key_findings=key_findings,
            supplemental=supplemental_findings,
            engines=material['engines_used'],
            degradation=material['degradation_info'],
        )

        packet = FinalReportPacket(
            review_id=brief.review_id,
            final_grade=final_grade,
            executive_summary=executive_summary,
            top_risks=top_risks,
            key_findings=key_findings,
            supplemental_findings=supplemental_findings,
            all_findings=all_findings,
            traceability=material['traceability'],
            report_markdown=report_markdown,
            engines_used=material['engines_used'],
            degradation_info=material['degradation_info'],
            produced_at=datetime.now(timezone.utc),
            source_packets=material['source_packets'],
        )

        self._annotate_final_decision_findings(
            packet,
            support_packet_008=support_packet_008,
            hermes_review_packet=hermes_review_packet,
        )
        return packet

    def _decide_grade(self, all_findings: list[FindingItem]) -> str:
        high = sum(1 for finding in all_findings if finding.severity == 'high')
        medium = sum(1 for finding in all_findings if finding.severity == 'medium')
        if high >= 3:
            return 'fail'
        if high >= 1 or medium >= 5:
            return 'needs_revision'
        return 'conditional_pass'

    def _decide_executive_summary(
        self,
        metrics: ReviewPacketMetrics,
        hermes_packet: FactPacket | None,
        supplemental_count: int,
        grade: str,
    ) -> str:
        lines = [
            f"本次审查由 Hermes 裁决，综合评级：**{_GRADE_LABELS.get(grade, grade)}**。",
            f"底层结构化引擎提供支持，发现 {metrics.total_findings} 个基础事实（高 {metrics.high_severity}，中 {metrics.medium_severity}，低 {metrics.low_severity}）。",
        ]
        if hermes_packet and not hermes_packet.degraded:
            lines.append(f"Hermes 主控层补充裁定 {supplemental_count} 个独立问题/风险。")
        elif hermes_packet and hermes_packet.degraded:
            lines.append(f"Hermes 主控层本次处于降级模式（{hermes_packet.error}），裁决基于降级保障。")
        return ' '.join(lines)

    def _render_markdown(
        self,
        doc_label: str,
        summary: str,
        top_risks: list[FindingItem],
        key_findings: list[FindingItem],
        supplemental: list[FindingItem],
        engines: list[str],
        degradation: dict[str, Any],
    ) -> str:
        lines: list[str] = []
        lines.append(f'# {doc_label} — 综合审查报告\n')
        lines.append(f'## Hermes 最终裁决\n\n{summary}\n')

        if top_risks:
            lines.append('## 重点风险\n')
            for finding in top_risks:
                lines.append(f'- **[{finding.severity.upper()}]** {finding.title}')
                if finding.summary:
                    lines.append(f'  {finding.summary[:200]}')
            lines.append('')

        if key_findings:
            lines.append('## 支撑问题 (底层提取)\n')
            lines.append('| 编号 | 严重度 | 来源 | 问题 | 建议 |')
            lines.append('|------|--------|------|------|------|')
            for finding in key_findings:
                source = finding.source_engine or '008'
                corroborated = ' ✓' if (finding.raw_data or {}).get('corroborated_by_hermes') else ''
                suggestion = (finding.suggestion[:80] + '…') if finding.suggestion and len(finding.suggestion) > 80 else (finding.suggestion or '')
                lines.append(f'| {finding.id} | {finding.severity} | {source}{corroborated} | {finding.title} | {suggestion} |')
            lines.append('')

        if supplemental:
            lines.append('## 主审独立问题\n')
            for finding in supplemental:
                lines.append(f'- **[{finding.id}]** [{finding.severity}] {finding.title}')
                if finding.summary:
                    lines.append(f'  {finding.summary[:200]}')
                if finding.suggestion:
                    lines.append(f'  建议: {finding.suggestion[:200]}')
            lines.append('')

        lines.append('## 审查引擎信息\n')
        lines.append(f"- 使用引擎: {', '.join(engines)}")
        for engine, info in degradation.items():
            lines.append(f"- {engine} 降级: {info.get('reason', 'unknown')}")
        lines.append('')
        return '\n'.join(lines)

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
