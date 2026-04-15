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
    'hazardous_special_scheme_staffing_completeness': ['hazardous_scheme_structure'],
    'hazardous_special_scheme_acceptance_completeness': ['hazardous_scheme_structure'],
    'hazardous_special_scheme_drawing_visibility': ['hazardous_scheme_drawings', 'review_visibility_gap'],
    'hazardous_special_scheme_risk_identification_completeness': ['hazardous_scheme_structure'],
    'hazardous_special_scheme_layout_and_environment_completeness': ['hazardous_scheme_structure'],
    'hazardous_special_scheme_attachment_visibility': ['review_visibility_gap'],
    'hazardous_special_scheme_calculation_evidence': ['hazardous_scheme_calculation'],
    'hazardous_special_scheme_emergency_targeted': ['emergency_plan_targeted'],
    'hazardous_special_scheme_measure_linkage': ['hazardous_scheme_measures'],
    'foundation_pit_structure_completeness': ['foundation_pit_structure'],
    'foundation_pit_monitoring_and_drawings': ['foundation_pit_monitoring', 'review_visibility_gap'],
    'foundation_pit_support_sequence_integrity': ['foundation_pit_sequence'],
    'foundation_pit_acceptance_completeness': ['foundation_pit_acceptance'],
    'formwork_support_structure_completeness': ['formwork_support_structure'],
    'formwork_support_process_parameters': ['formwork_support_process'],
    'formwork_support_calculation_traceability': ['formwork_support_calculation'],
    'formwork_support_acceptance_completeness': ['formwork_support_acceptance'],
    'lifting_installation_removal_scheme_integrity': ['lifting_installation_removal_scheme'],
    'lifting_installation_removal_site_bearing_traceability': ['lifting_installation_removal_site_bearing'],
    'lifting_installation_removal_temporary_fixation_completeness': ['lifting_installation_removal_fixation'],
    'lifting_installation_removal_drawing_visibility': ['lifting_installation_removal_drawings', 'review_visibility_gap'],
    'scaffold_structure_parameters_completeness': ['scaffold_structure'],
    'scaffold_safety_device_and_wall_tie_completeness': ['scaffold_safety'],
    'scaffold_monitoring_and_acceptance_completeness': ['scaffold_monitoring_acceptance'],
    'demolition_sequence_integrity': ['demolition_sequence'],
    'demolition_retained_structure_control_completeness': ['demolition_retained_structure'],
    'demolition_support_calculation_traceability': ['demolition_calculation'],
    'underground_excavation_water_control_completeness': ['underground_excavation_water_control'],
    'underground_excavation_support_parameters_completeness': ['underground_excavation_support_parameters'],
    'underground_excavation_monitoring_and_drawings': ['underground_excavation_monitoring', 'review_visibility_gap'],
    'curtain_wall_installation_facility_integrity': ['curtain_wall_installation_facility'],
    'curtain_wall_installation_route_and_layout_completeness': ['curtain_wall_installation_route_layout'],
    'curtain_wall_installation_drawing_and_acceptance': ['curtain_wall_installation_drawings', 'review_visibility_gap'],
    'manual_bored_pile_jump_excavation_integrity': ['manual_bored_pile_jump_excavation'],
    'manual_bored_pile_gas_and_electric_safety_completeness': ['manual_bored_pile_gas_electric_safety'],
    'manual_bored_pile_forbidden_conditions_manual_review': ['manual_bored_pile_forbidden_conditions'],
    'steel_structure_installation_structure_completeness': ['steel_structure_installation_structure'],
    'steel_structure_installation_lifting_scheme_integrity': ['steel_structure_installation_scheme'],
    'steel_structure_installation_support_and_unloading': ['steel_structure_installation_support'],
    'steel_structure_installation_drawing_and_acceptance': ['steel_structure_installation_drawings', 'review_visibility_gap'],
    'supervision_plan_structure_completeness': ['supervision_plan_structure'],
    'supervision_plan_monitoring_linkage': ['supervision_plan_monitoring'],
    'supervision_plan_attachment_visibility': ['review_visibility_gap'],
    'review_support_material_context_only': ['review_support_material_context'],
    'review_support_material_attachment_visibility': ['review_visibility_gap'],
    'distribution_network_special_scheme_structure_completeness': ['distribution_network_special_scheme_structure'],
    'distribution_network_special_scheme_risk_identification': ['distribution_network_special_scheme_risk_identification'],
    'distribution_network_special_scheme_drawings_and_boundary': ['distribution_network_special_scheme_drawings', 'review_visibility_gap'],
    'distribution_network_special_scheme_emergency_targeted': ['distribution_network_special_scheme_emergency', 'emergency_plan_targeted'],
    'power_outage_work_structure_completeness': ['power_outage_work_structure'],
    'power_outage_work_safety_and_quality_controls': ['power_outage_work_controls', 'power_outage_work_acceptance_50254'],
    'power_outage_work_ticket_grounding_traceability': ['power_outage_work_ticket_grounding', 'power_outage_work_ticket_and_operation_26860', 'power_outage_work_five_step_26860'],
    'power_outage_work_basic_info_integrity': ['power_outage_work_basic_info'],
    'power_outage_work_personnel_qualification_and_training': ['power_outage_work_personnel_training'],
    'power_outage_work_application_approval_linkage': ['power_outage_work_application_approval', 'power_outage_work_application_approval_26860'],
    'power_outage_work_shutdown_five_step_closure': ['power_outage_work_five_step', 'power_outage_work_five_step_26860'],
    'power_outage_work_anti_backfeed_controls': ['power_outage_work_anti_backfeed', 'power_outage_work_anti_backfeed_26860'],
    'power_outage_work_work_ticket_and_site_survey': ['power_outage_work_ticket_grounding', 'power_outage_work_ticket_and_operation_26860'],
    'power_outage_work_restoration_and_archive_closure': ['power_outage_work_restoration_closure', 'power_outage_work_restoration_26860', 'power_outage_work_acceptance_50254'],
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
