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

class FinalReportMerger:
    """Prepare 008 primary and Hermes supplemental packets into fused materials."""

    def prepare_decision_material(
        self,
        brief: ReviewBrief,
        packet_008: FactPacket,
        packet_hermes: FactPacket | None = None,
    ) -> dict[str, Any]:
        logger.info('[final_report_merger] Preparing decision material for review %s', brief.review_id)

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

        return {
            'key_findings': key_findings,
            'supplemental_findings': supplemental_findings,
            'all_findings': all_findings,
            'traceability': traceability,
            'engines_used': engines_used,
            'degradation_info': degradation_info,
            'doc_label': _DOC_TYPE_LABELS.get(str(brief.review_object_type), str(brief.review_object_type)),
            'source_packets': {
                '008': packet_008.model_dump(mode='json', exclude={'raw_result'}),
                **({'hermes': packet_hermes.model_dump(mode='json', exclude={'raw_result'})} if packet_hermes else {}),
            }
        }

    def _build_corroboration_map(self, packet_hermes: FactPacket | None) -> dict[str, list[str]]:
        if not packet_hermes:
            return {}
        out: dict[str, list[str]] = {}
        for hermes_finding in packet_hermes.findings:
            ref = (hermes_finding.raw_data or {}).get('corroborates_008_finding')
            if ref and isinstance(ref, str):
                out.setdefault(ref, []).append(hermes_finding.id)
        return out
