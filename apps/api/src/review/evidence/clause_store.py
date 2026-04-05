from __future__ import annotations

from src.domain.models import ConfidenceLevel, EvidenceSpan
from src.review.evidence.packs import get_evidence_pack_registry
from src.review.schema import EvidencePack, PolicyClause


_RULE_TO_CLAUSE_IDS = {
    'construction_org_structure_completeness': ['construction_org_structure'],
    'construction_org_duplicate_sections': ['construction_org_structure'],
    'construction_org_attachment_visibility': ['review_visibility_gap'],
    'construction_org_special_scheme_gap': ['dangerous_special_scheme'],
    'construction_org_emergency_plan_targeted': ['emergency_plan_targeted'],
    'construction_org_shutdown_resource_conflict': ['construction_org_schedule_resource'],
    'construction_scheme_structure_completeness': ['construction_scheme_structure'],
    'construction_scheme_attachment_visibility': ['review_visibility_gap'],
    'hazardous_special_scheme_core_sections': ['hazardous_scheme_structure'],
    'hazardous_special_scheme_attachment_visibility': ['review_visibility_gap'],
    'hazardous_special_scheme_calculation_evidence': ['hazardous_scheme_calculation'],
    'hazardous_special_scheme_emergency_targeted': ['emergency_plan_targeted'],
    'hazardous_special_scheme_measure_linkage': ['hazardous_scheme_measures'],
    'supervision_plan_structure_completeness': ['supervision_plan_structure'],
    'supervision_plan_monitoring_linkage': ['supervision_plan_monitoring'],
    'supervision_plan_attachment_visibility': ['review_visibility_gap'],
    'review_support_material_context_only': ['review_support_material_context'],
    'review_support_material_attachment_visibility': ['review_visibility_gap'],
    'lifting_operations_special_scheme_linkage': ['dangerous_special_scheme'],
    'lifting_operations_calculation_traceability': ['hazardous_scheme_calculation'],
    'temporary_power_control_linkage': ['hazardous_scheme_measures', 'emergency_plan_targeted'],
    'hot_work_emergency_targeted': ['emergency_plan_targeted'],
    'gas_area_ops_control_linkage': ['hazardous_scheme_measures', 'emergency_plan_targeted'],
}


class ClauseStore:
    def __init__(self, evidence_packs: dict[str, EvidencePack] | None = None):
        self._packs = evidence_packs or get_evidence_pack_registry()
        self._clauses: dict[str, PolicyClause] = {}
        for pack in self._packs.values():
            for clause in pack.clauses:
                self._clauses[clause.id] = clause

    def get_policy_evidence(self, rule_id: str, pack_ids: list[str] | None = None) -> list[EvidenceSpan]:
        evidence: list[EvidenceSpan] = []
        for clause_id in _RULE_TO_CLAUSE_IDS.get(rule_id, []):
            clause = self._clauses.get(clause_id)
            if clause is None:
                continue
            evidence.append(
                EvidenceSpan(
                    sourceType='policy',
                    sourceId=clause.sourceId,
                    locator={'clauseId': clause.id},
                    excerpt=clause.excerpt,
                    confidence=ConfidenceLevel.high,
                    clauseTitle=clause.title,
                    forceLevel=clause.forceLevel,
                    applicability=clause.applicability,
                    sourceProvenance=clause.sourceId,
                )
            )
        return evidence

    def get_clause_ids(self, rule_id: str) -> list[str]:
        return list(_RULE_TO_CLAUSE_IDS.get(rule_id, []))
