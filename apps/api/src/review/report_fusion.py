"""
Report Fusion Service: merges 008 + Hermes packets into a FinalReportPacket.

V1 fusion rules:
    1. 008 findings → always key_findings (primary engine)
    2. Hermes findings that corroborate 008 → annotate the 008 finding
    3. Hermes-only findings → supplemental_findings
    4. top_risks = high severity from any engine
    5. Hermes degraded or absent → report based on 008 only (graceful)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from src.review.contracts import (
    FactPacket,
    FinalReportPacket,
    FindingItem,
    ReviewBrief,
)

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


class ReportFusionService:
    """Merge 008 + Hermes review packets into a final traceable report."""

    def fuse(
        self,
        brief: ReviewBrief,
        packet_008: FactPacket,
        packet_hermes: FactPacket | None = None,
    ) -> FinalReportPacket:
        logger.info('[fusion] Starting for review %s', brief.review_id)

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

        # --- Corroboration map ---
        corroboration_map = self._build_corroboration_map(packet_hermes) if hermes_ok else {}

        # --- Classify findings ---
        key_findings: list[FindingItem] = []
        supplemental_findings: list[FindingItem] = []
        all_findings: list[FindingItem] = []
        traceability: list[dict[str, Any]] = []

        # 008 findings (always primary)
        for f in packet_008.findings:
            tagged = f.model_copy()
            corr_by = corroboration_map.get(f.id, [])
            if corr_by:
                tagged.raw_data = {**tagged.raw_data, 'corroborated_by_hermes': corr_by}
            key_findings.append(tagged)
            all_findings.append(tagged)
            traceability.append({
                'finding_id': tagged.id,
                'source_engine': '008',
                'corroborated': bool(corr_by),
            })

        # Hermes findings
        if hermes_ok and packet_hermes is not None:
            corroborated_ids = {hid for ids in corroboration_map.values() for hid in ids}
            for f in packet_hermes.findings:
                if f.id in corroborated_ids:
                    traceability.append({
                        'finding_id': f.id,
                        'source_engine': 'hermes',
                        'merged_into_008': True,
                    })
                    continue
                supplemental_findings.append(f)
                all_findings.append(f)
                traceability.append({
                    'finding_id': f.id,
                    'source_engine': 'hermes',
                    'corroborated': False,
                })

        top_risks = [f for f in all_findings if f.severity == 'high']
        final_grade = self._grade(key_findings)
        exec_summary = self._executive_summary(
            packet_008, packet_hermes, supplemental_findings, final_grade,
        )
        report_md = self._render_markdown(
            brief, exec_summary, final_grade,
            top_risks, key_findings, supplemental_findings,
            engines_used, degradation_info,
        )

        packet = FinalReportPacket(
            review_id=brief.review_id,
            final_grade=final_grade,
            executive_summary=exec_summary,
            top_risks=top_risks,
            key_findings=key_findings,
            supplemental_findings=supplemental_findings,
            all_findings=all_findings,
            traceability=traceability,
            report_markdown=report_md,
            engines_used=engines_used,
            degradation_info=degradation_info,
            produced_at=datetime.now(timezone.utc),
            source_packets={
                '008': packet_008.model_dump(mode='json', exclude={'raw_result'}),
                **(
                    {'hermes': packet_hermes.model_dump(mode='json', exclude={'raw_result'})}
                    if packet_hermes else {}
                ),
            },
        )
        logger.info(
            '[fusion] Done: grade=%s key=%d suppl=%d engines=%s',
            final_grade, len(key_findings), len(supplemental_findings), engines_used,
        )
        return packet

    # ------------------------------------------------------------------

    def _build_corroboration_map(self, packet_hermes: FactPacket | None) -> dict[str, list[str]]:
        if not packet_hermes:
            return {}
        out: dict[str, list[str]] = {}
        for hf in packet_hermes.findings:
            ref = (hf.raw_data or {}).get('corroborates_008_finding')
            if ref and isinstance(ref, str):
                out.setdefault(ref, []).append(hf.id)
        return out

    def _grade(self, key_findings: list[FindingItem]) -> str:
        high = sum(1 for f in key_findings if f.severity == 'high')
        med = sum(1 for f in key_findings if f.severity == 'medium')
        if high >= 3:
            return 'fail'
        if high >= 1 or med >= 5:
            return 'needs_revision'
        return 'conditional_pass'

    def _executive_summary(
        self,
        p008: FactPacket,
        phermes: FactPacket | None,
        supplemental: list,
        grade: str,
    ) -> str:
        m = p008.summary_metrics
        lines = [
            f"本次审查综合评级：**{_GRADE_LABELS.get(grade, grade)}**。",
            f"008引擎发现 {m.total_findings} 个问题"
            f"（高 {m.high_severity}，中 {m.medium_severity}，低 {m.low_severity}）。",
        ]
        if phermes and not phermes.degraded:
            lines.append(f"Hermes引擎补充发现 {len(supplemental)} 个独立问题。")
        elif phermes and phermes.degraded:
            lines.append(f"Hermes引擎本次未能参与审查（{phermes.error}），报告基于008单路结果。")
        return ' '.join(lines)

    def _render_markdown(
        self,
        brief: ReviewBrief,
        summary: str,
        grade: str,
        top_risks: list[FindingItem],
        key_findings: list[FindingItem],
        supplemental: list[FindingItem],
        engines: list[str],
        degradation: dict,
    ) -> str:
        doc_label = _DOC_TYPE_LABELS.get(str(brief.review_object_type), str(brief.review_object_type))
        s: list[str] = []
        s.append(f'# {doc_label} — 综合审查报告\n')
        s.append(f'## 综合评估\n\n{summary}\n')

        if top_risks:
            s.append('## 重点风险\n')
            for r in top_risks:
                s.append(f'- **[{r.severity.upper()}]** {r.title}')
                if r.summary:
                    s.append(f'  {r.summary[:200]}')
            s.append('')

        if key_findings:
            s.append('## 主要问题\n')
            s.append('| 编号 | 严重度 | 来源 | 问题 | 建议 |')
            s.append('|------|--------|------|------|------|')
            for f in key_findings:
                src = f.source_engine or '008'
                corr = ' ✓' if (f.raw_data or {}).get('corroborated_by_hermes') else ''
                sug = (f.suggestion[:80] + '…') if f.suggestion and len(f.suggestion) > 80 else (f.suggestion or '')
                s.append(f'| {f.id} | {f.severity} | {src}{corr} | {f.title} | {sug} |')
            s.append('')

        if supplemental:
            s.append('## 补充关注项（Hermes 独立发现）\n')
            for f in supplemental:
                s.append(f'- **[{f.id}]** [{f.severity}] {f.title}')
                if f.summary:
                    s.append(f'  {f.summary[:200]}')
                if f.suggestion:
                    s.append(f'  建议: {f.suggestion[:200]}')
            s.append('')

        s.append('## 审查引擎信息\n')
        s.append(f"- 使用引擎: {', '.join(engines)}")
        for engine, info in degradation.items():
            s.append(f"- {engine} 降级: {info.get('reason', 'unknown')}")
        s.append('')
        return '\n'.join(s)
