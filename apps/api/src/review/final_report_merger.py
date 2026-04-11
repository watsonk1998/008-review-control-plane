"""Assembler-internal final report merger for HermesController-first structured review.

Status:
- internal helper / legacy-helper semantics

Freeze boundary:
- merger logic only
- not a runtime entrypoint
- not an independently owned final-output path

Do not extend:
- no new direct call sites outside HermesReviewAssembler
- no route/runtime/controller protocol ownership
- no 008 internal schema ownership

Canonical path:
- HermesReviewAssembler is the only official final output entrypoint
- FinalReportMerger exists only as an internal helper used by the assembler to fuse packets
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from src.review.contracts import FactPacket, FinalReportPacket, FindingItem, ReviewBrief

logger = logging.getLogger(__name__)

_DOC_TYPE_LABELS = {
    'construction_org': '施工组织设计',
    'construction_scheme': '施工方案',
    'hazardous_special_scheme': '危大工程专项施工方案',
    'distribution_network_special_scheme': '配网停电施工专项方案',
    'supervision_plan': '监理规划',
    'review_support_material': '审查辅助材料',
}

_GRADE_LABELS = {
    'conditional_pass': '有条件通过',
    'needs_revision': '需要修改',
    'fail': '不通过',
}


class FinalReportMerger:
    """Merge 008 primary and Hermes supplemental packets into one final packet."""

    def fuse(
        self,
        brief: ReviewBrief,
        packet_008: FactPacket,
        packet_hermes: FactPacket | None = None,
    ) -> FinalReportPacket:
        logger.info('[final_report_merger] Starting for review %s', brief.review_id)

        engines_used = ['008']
        degradation_info: dict[str, Any] = {}

        hermes_ok = packet_hermes is not None and not packet_hermes.degraded
        if hermes_ok:
            engines_used.append('hermes')
        elif packet_hermes and packet_hermes.degraded:
            degradation_info['hermes'] = {
                'status': 'degraded',
                'reason': packet_hermes.error or 'unknown',
            }

        corroboration_map = self._build_corroboration_map(packet_hermes) if hermes_ok else {}

        key_findings: list[FindingItem] = []
        supplemental_findings: list[FindingItem] = []
        all_findings: list[FindingItem] = []
        traceability: list[dict[str, Any]] = []

        for finding in packet_008.findings:
            tagged = finding.model_copy()
            corr_by = corroboration_map.get(finding.id, [])
            if corr_by:
                tagged.raw_data = {**tagged.raw_data, 'corroborated_by_hermes': corr_by}
            key_findings.append(tagged)
            all_findings.append(tagged)
            traceability.append({
                'finding_id': tagged.id,
                'source_engine': '008',
                'corroborated': bool(corr_by),
            })

        if hermes_ok and packet_hermes is not None:
            corroborated_ids = {hid for ids in corroboration_map.values() for hid in ids}
            for finding in packet_hermes.findings:
                if finding.id in corroborated_ids:
                    traceability.append({
                        'finding_id': finding.id,
                        'source_engine': 'hermes',
                        'merged_into_008': True,
                    })
                    continue
                supplemental_findings.append(finding)
                all_findings.append(finding)
                traceability.append({
                    'finding_id': finding.id,
                    'source_engine': 'hermes',
                    'corroborated': False,
                })

        top_risks = [item for item in all_findings if item.severity == 'high']
        final_grade = self._grade(key_findings)
        executive_summary = self._executive_summary(packet_008, packet_hermes, supplemental_findings, final_grade)
        report_markdown = self._render_markdown(
            brief,
            executive_summary,
            top_risks,
            key_findings,
            supplemental_findings,
            engines_used,
            degradation_info,
        )

        packet = FinalReportPacket(
            review_id=brief.review_id,
            final_grade=final_grade,
            executive_summary=executive_summary,
            top_risks=top_risks,
            key_findings=key_findings,
            supplemental_findings=supplemental_findings,
            all_findings=all_findings,
            traceability=traceability,
            report_markdown=report_markdown,
            engines_used=engines_used,
            degradation_info=degradation_info,
            produced_at=datetime.now(timezone.utc),
            source_packets={
                '008': packet_008.model_dump(mode='json', exclude={'raw_result'}),
                **({'hermes': packet_hermes.model_dump(mode='json', exclude={'raw_result'})} if packet_hermes else {}),
            },
        )
        logger.info(
            '[final_report_merger] Done: grade=%s key=%d suppl=%d engines=%s',
            final_grade,
            len(key_findings),
            len(supplemental_findings),
            engines_used,
        )
        return packet

    def _build_corroboration_map(self, packet_hermes: FactPacket | None) -> dict[str, list[str]]:
        if not packet_hermes:
            return {}
        out: dict[str, list[str]] = {}
        for hermes_finding in packet_hermes.findings:
            ref = (hermes_finding.raw_data or {}).get('corroborates_008_finding')
            if ref and isinstance(ref, str):
                out.setdefault(ref, []).append(hermes_finding.id)
        return out

    def _grade(self, key_findings: list[FindingItem]) -> str:
        high = sum(1 for finding in key_findings if finding.severity == 'high')
        medium = sum(1 for finding in key_findings if finding.severity == 'medium')
        if high >= 3:
            return 'fail'
        if high >= 1 or medium >= 5:
            return 'needs_revision'
        return 'conditional_pass'

    def _executive_summary(
        self,
        packet_008: FactPacket,
        packet_hermes: FactPacket | None,
        supplemental_findings: list[FindingItem],
        grade: str,
    ) -> str:
        metrics = packet_008.summary_metrics
        lines = [
            f"本次审查综合评级：**{_GRADE_LABELS.get(grade, grade)}**。",
            f"008引擎发现 {metrics.total_findings} 个问题（高 {metrics.high_severity}，中 {metrics.medium_severity}，低 {metrics.low_severity}）。",
        ]
        if packet_hermes and not packet_hermes.degraded:
            lines.append(f"Hermes补充发现 {len(supplemental_findings)} 个独立问题。")
        elif packet_hermes and packet_hermes.degraded:
            lines.append(f"Hermes本次未能参与补充审查（{packet_hermes.error}），最终报告基于008主审查结果。")
        return ' '.join(lines)

    def _render_markdown(
        self,
        brief: ReviewBrief,
        summary: str,
        top_risks: list[FindingItem],
        key_findings: list[FindingItem],
        supplemental: list[FindingItem],
        engines: list[str],
        degradation: dict[str, Any],
    ) -> str:
        doc_label = _DOC_TYPE_LABELS.get(str(brief.review_object_type), str(brief.review_object_type))
        lines: list[str] = []
        lines.append(f'# {doc_label} — 综合审查报告\n')
        lines.append(f'## 综合评估\n\n{summary}\n')

        if top_risks:
            lines.append('## 重点风险\n')
            for finding in top_risks:
                lines.append(f'- **[{finding.severity.upper()}]** {finding.title}')
                if finding.summary:
                    lines.append(f'  {finding.summary[:200]}')
            lines.append('')

        if key_findings:
            lines.append('## 主要问题\n')
            lines.append('| 编号 | 严重度 | 来源 | 问题 | 建议 |')
            lines.append('|------|--------|------|------|------|')
            for finding in key_findings:
                source = finding.source_engine or '008'
                corroborated = ' ✓' if (finding.raw_data or {}).get('corroborated_by_hermes') else ''
                suggestion = (finding.suggestion[:80] + '…') if finding.suggestion and len(finding.suggestion) > 80 else (finding.suggestion or '')
                lines.append(f'| {finding.id} | {finding.severity} | {source}{corroborated} | {finding.title} | {suggestion} |')
            lines.append('')

        if supplemental:
            lines.append('## 补充关注项\n')
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
