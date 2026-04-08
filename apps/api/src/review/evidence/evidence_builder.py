from __future__ import annotations

from src.domain.models import FindingType
from src.review.evidence.clause_store import ClauseStore
from src.review.schema import ExtractedFacts, IssueCandidate, RuleHit


class EvidenceBuilder:
    def __init__(self, clause_store: ClauseStore | None = None):
        self.clause_store = clause_store or ClauseStore()
        self._titles = {
            'construction_org_structure_completeness': '施工组织设计核心章节不完整',
            'construction_org_duplicate_sections': '章节结构存在重复标题，正式审查定位不稳定',
            'construction_org_attachment_visibility': '附件处于可视域缺口，需人工复核原件',
            'construction_org_special_scheme_gap': '高风险作业已识别，但专项方案挂接不清',
            'construction_org_emergency_plan_targeted': '应急预案针对性不足',
            'construction_org_shutdown_resource_conflict': '停机窗口、投入人力与高风险工序并行存在组织压力',
            'construction_scheme_structure_completeness': '一般施工方案核心章节不完整',
            'construction_scheme_attachment_visibility': '施工方案附件处于可视域缺口，需人工复核原件',
            'hazardous_special_scheme_core_sections': '危大专项方案核心章节不完整',
            'hazardous_special_scheme_staffing_completeness': '危大专项方案缺少人员配备与分工章节',
            'hazardous_special_scheme_acceptance_completeness': '危大专项方案缺少验收要求章节',
            'hazardous_special_scheme_drawing_visibility': '危大专项方案相关图纸需人工复核',
            'hazardous_special_scheme_risk_identification_completeness': '危大专项方案缺少风险辨识与分级章节',
            'hazardous_special_scheme_layout_and_environment_completeness': '危大专项方案缺少平面布置或周边环境章节',
            'hazardous_special_scheme_attachment_visibility': '专项方案附件处于可视域缺口，需人工复核原件',
            'hazardous_special_scheme_calculation_evidence': '专项方案缺少可追溯验算依据',
            'hazardous_special_scheme_emergency_targeted': '专项方案应急处置安排针对性不足',
            'hazardous_special_scheme_measure_linkage': '主要危险源、控制措施与监测监控闭环不足',
            'foundation_pit_structure_completeness': '基坑工程专项章节不完整',
            'foundation_pit_monitoring_and_drawings': '基坑工程监测图纸或监测章节需人工复核',
            'foundation_pit_support_sequence_integrity': '基坑工程未明确支护、降水与开挖关系',
            'foundation_pit_acceptance_completeness': '基坑工程验收要求不完整',
            'formwork_support_structure_completeness': '模板支撑体系专项章节不完整',
            'formwork_support_process_parameters': '模板支撑体系关键工艺参数或浇筑顺序不完整',
            'formwork_support_calculation_traceability': '模板支撑体系缺少可追溯计算依据',
            'formwork_support_acceptance_completeness': '模板支撑体系验收要求不完整',
            'lifting_installation_removal_scheme_integrity': '起重吊装及安装拆卸方案骨架不完整',
            'lifting_installation_removal_site_bearing_traceability': '起重吊装及安装拆卸缺少站位承载依据',
            'lifting_installation_removal_temporary_fixation_completeness': '起重吊装及安装拆卸缺少临时固定或辅助装置说明',
            'lifting_installation_removal_drawing_visibility': '起重吊装及安装拆卸图纸需人工复核',
            'scaffold_structure_parameters_completeness': '脚手架工程结构参数不完整',
            'scaffold_safety_device_and_wall_tie_completeness': '脚手架工程缺少连墙件或防坠落装置说明',
            'scaffold_monitoring_and_acceptance_completeness': '脚手架工程监测或验收要求不完整',
            'demolition_sequence_integrity': '拆除工程拆除顺序不完整',
            'demolition_retained_structure_control_completeness': '拆除工程缺少保留结构或平台控制要求',
            'demolition_support_calculation_traceability': '拆除工程缺少临时支撑或吊运计算依据',
            'underground_excavation_water_control_completeness': '暗挖工程缺少地下水控制措施',
            'underground_excavation_support_parameters_completeness': '暗挖工程支护参数不完整',
            'underground_excavation_monitoring_and_drawings': '暗挖工程监测图纸需人工复核',
            'curtain_wall_installation_facility_integrity': '建筑幕墙安装设施或防护措施不完整',
            'curtain_wall_installation_route_and_layout_completeness': '建筑幕墙安装缺少运输路线或平面布置',
            'curtain_wall_installation_drawing_and_acceptance': '建筑幕墙安装图纸或验收章节需人工复核',
            'manual_bored_pile_jump_excavation_integrity': '人工挖孔桩缺少跳挖或分序要求',
            'manual_bored_pile_gas_and_electric_safety_completeness': '人工挖孔桩缺少防中毒窒息或防触电措施',
            'manual_bored_pile_forbidden_conditions_manual_review': '人工挖孔桩禁用条件需人工复核',
            'steel_structure_installation_structure_completeness': '钢结构安装专项章节不完整',
            'steel_structure_installation_lifting_scheme_integrity': '钢结构安装吊装方案关键信息不完整',
            'steel_structure_installation_support_and_unloading': '钢结构安装缺少临时支撑或卸载条件',
            'steel_structure_installation_drawing_and_acceptance': '钢结构安装图纸或验收章节需人工复核',
            'supervision_plan_structure_completeness': '监理规划核心章节不完整',
            'supervision_plan_monitoring_linkage': '监理规划缺少明确的监测监控/旁站安排',
            'supervision_plan_attachment_visibility': '监理规划附件处于可视域缺口，需人工复核原件',
            'review_support_material_context_only': '审查支持材料不能替代正式方案正文',
            'review_support_material_attachment_visibility': '审查支持材料附件处于可视域缺口，需人工复核原件',
            'distribution_network_special_scheme_structure_completeness': '配网工程专项施工方案通用章节不完整',
            'power_outage_work_structure_completeness': '停电施工作业专项章节不完整',
            'lifting_operations_special_scheme_linkage': '起重吊装场景专项方案挂接不清',
            'lifting_operations_calculation_traceability': '起重吊装关键参数或验算依据不可追溯',
            'temporary_power_control_linkage': '临时用电/停送电控制链路不完整',
            'hot_work_emergency_targeted': '动火作业缺少火灾类针对性应急安排',
            'gas_area_ops_control_linkage': '煤气区域作业控制与应急链路不完整',
        }
        self._finding_types = {
            'construction_org_structure_completeness': FindingType.hard_evidence,
            'construction_org_duplicate_sections': FindingType.hard_evidence,
            'construction_org_attachment_visibility': FindingType.visibility_gap,
            'construction_org_special_scheme_gap': FindingType.hard_evidence,
            'construction_org_emergency_plan_targeted': FindingType.hard_evidence,
            'construction_org_shutdown_resource_conflict': FindingType.engineering_inference,
            'construction_scheme_structure_completeness': FindingType.hard_evidence,
            'construction_scheme_attachment_visibility': FindingType.visibility_gap,
            'hazardous_special_scheme_core_sections': FindingType.hard_evidence,
            'hazardous_special_scheme_staffing_completeness': FindingType.hard_evidence,
            'hazardous_special_scheme_acceptance_completeness': FindingType.hard_evidence,
            'hazardous_special_scheme_drawing_visibility': FindingType.visibility_gap,
            'hazardous_special_scheme_risk_identification_completeness': FindingType.hard_evidence,
            'hazardous_special_scheme_layout_and_environment_completeness': FindingType.hard_evidence,
            'hazardous_special_scheme_attachment_visibility': FindingType.visibility_gap,
            'hazardous_special_scheme_calculation_evidence': FindingType.hard_evidence,
            'hazardous_special_scheme_emergency_targeted': FindingType.hard_evidence,
            'hazardous_special_scheme_measure_linkage': FindingType.engineering_inference,
            'foundation_pit_structure_completeness': FindingType.hard_evidence,
            'foundation_pit_monitoring_and_drawings': FindingType.visibility_gap,
            'foundation_pit_support_sequence_integrity': FindingType.hard_evidence,
            'foundation_pit_acceptance_completeness': FindingType.hard_evidence,
            'formwork_support_structure_completeness': FindingType.hard_evidence,
            'formwork_support_process_parameters': FindingType.hard_evidence,
            'formwork_support_calculation_traceability': FindingType.hard_evidence,
            'formwork_support_acceptance_completeness': FindingType.hard_evidence,
            'lifting_installation_removal_scheme_integrity': FindingType.hard_evidence,
            'lifting_installation_removal_site_bearing_traceability': FindingType.hard_evidence,
            'lifting_installation_removal_temporary_fixation_completeness': FindingType.hard_evidence,
            'lifting_installation_removal_drawing_visibility': FindingType.visibility_gap,
            'scaffold_structure_parameters_completeness': FindingType.hard_evidence,
            'scaffold_safety_device_and_wall_tie_completeness': FindingType.hard_evidence,
            'scaffold_monitoring_and_acceptance_completeness': FindingType.hard_evidence,
            'demolition_sequence_integrity': FindingType.hard_evidence,
            'demolition_retained_structure_control_completeness': FindingType.hard_evidence,
            'demolition_support_calculation_traceability': FindingType.hard_evidence,
            'underground_excavation_water_control_completeness': FindingType.hard_evidence,
            'underground_excavation_support_parameters_completeness': FindingType.hard_evidence,
            'underground_excavation_monitoring_and_drawings': FindingType.visibility_gap,
            'curtain_wall_installation_facility_integrity': FindingType.hard_evidence,
            'curtain_wall_installation_route_and_layout_completeness': FindingType.hard_evidence,
            'curtain_wall_installation_drawing_and_acceptance': FindingType.visibility_gap,
            'manual_bored_pile_jump_excavation_integrity': FindingType.hard_evidence,
            'manual_bored_pile_gas_and_electric_safety_completeness': FindingType.hard_evidence,
            'manual_bored_pile_forbidden_conditions_manual_review': FindingType.visibility_gap,
            'steel_structure_installation_structure_completeness': FindingType.hard_evidence,
            'steel_structure_installation_lifting_scheme_integrity': FindingType.hard_evidence,
            'steel_structure_installation_support_and_unloading': FindingType.hard_evidence,
            'steel_structure_installation_drawing_and_acceptance': FindingType.visibility_gap,
            'supervision_plan_structure_completeness': FindingType.hard_evidence,
            'supervision_plan_monitoring_linkage': FindingType.hard_evidence,
            'supervision_plan_attachment_visibility': FindingType.visibility_gap,
            'review_support_material_context_only': FindingType.suggestion_enhancement,
            'review_support_material_attachment_visibility': FindingType.visibility_gap,
            'distribution_network_special_scheme_structure_completeness': FindingType.hard_evidence,
            'power_outage_work_structure_completeness': FindingType.hard_evidence,
            'lifting_operations_special_scheme_linkage': FindingType.hard_evidence,
            'lifting_operations_calculation_traceability': FindingType.hard_evidence,
            'temporary_power_control_linkage': FindingType.engineering_inference,
            'hot_work_emergency_targeted': FindingType.hard_evidence,
            'gas_area_ops_control_linkage': FindingType.engineering_inference,
        }
        self._manual_review_reasons = {
            'construction_org_attachment_visibility': 'visibility_gap',
            'construction_scheme_attachment_visibility': 'visibility_gap',
            'hazardous_special_scheme_attachment_visibility': 'visibility_gap',
            'hazardous_special_scheme_drawing_visibility': 'drawing_visibility_gap',
            'foundation_pit_monitoring_and_drawings': 'drawing_visibility_gap',
            'lifting_installation_removal_drawing_visibility': 'drawing_visibility_gap',
            'underground_excavation_monitoring_and_drawings': 'drawing_visibility_gap',
            'curtain_wall_installation_drawing_and_acceptance': 'drawing_visibility_gap',
            'manual_bored_pile_forbidden_conditions_manual_review': 'forbidden_condition_requires_manual_confirmation',
            'steel_structure_installation_drawing_and_acceptance': 'drawing_visibility_gap',
            'supervision_plan_attachment_visibility': 'visibility_gap',
            'review_support_material_attachment_visibility': 'visibility_gap',
            'construction_org_special_scheme_gap': 'special_scheme_reference_requires_manual_confirmation',
            'lifting_operations_special_scheme_linkage': 'special_scheme_reference_requires_manual_confirmation',
        }
        self._closed_negative_fact_prefixes = ('project.sectionPresence.', 'project.structureCompleteness.')
        self._closed_negative_fact_keys = {
            'hazard.measureSectionPresent',
            'hazard.monitoringSectionPresent',
        }

    def build(self, rule_hits: list[RuleHit], facts: ExtractedFacts, parse_result, packs) -> list[IssueCandidate]:
        candidates: list[IssueCandidate] = []
        selected_pack_ids = [pack.id for pack in packs]
        for hit in rule_hits:
            if hit.status not in {'hit', 'manual_review_needed'}:
                continue
            doc_evidence = self._collect_doc_evidence(hit.factRefs, facts)
            policy_evidence = self.clause_store.get_policy_evidence(hit.ruleId, selected_pack_ids)
            base_finding_type = self._finding_types.get(hit.ruleId, FindingType.hard_evidence)
            visibility_gap = hit.applicabilityState == 'blocked_by_visibility' or any(
                span.visibility and span.visibility.value != 'parsed' for span in doc_evidence
            )
            manual_review_needed = hit.status == 'manual_review_needed' or hit.applicabilityState in {
                'blocked_by_visibility',
                'partial',
            }
            blocking_reasons = list(hit.blockingReasons)
            if hit.applicabilityState == 'blocked_by_visibility':
                evidence_missing = False
            elif hit.applicabilityState == 'blocked_by_missing_fact':
                evidence_missing = True
            else:
                closed_negative_hit = self._is_closed_negative_hit(hit)
                evidence_missing = False
                if not policy_evidence:
                    evidence_missing = True
                    blocking_reasons.append('policy_evidence_unavailable')
                elif not doc_evidence and not closed_negative_hit:
                    evidence_missing = True
                    blocking_reasons.append('document_evidence_unavailable')
            if visibility_gap:
                blocking_reasons.append('visibility_gap')
            if evidence_missing and hit.missingFactKeys:
                blocking_reasons.append('missing_fact')
            gap_reason = self._derive_gap_reason(
                applicability_state=hit.applicabilityState,
                blocking_reasons=blocking_reasons,
                manual_review_needed=manual_review_needed,
                evidence_missing=evidence_missing,
            )
            doc_evidence = self._annotate_evidence_spans(doc_evidence, gap_reason=gap_reason)
            policy_evidence = self._annotate_evidence_spans(policy_evidence, gap_reason=gap_reason)
            finding_type = FindingType.visibility_gap if hit.applicabilityState == 'blocked_by_visibility' else base_finding_type
            candidates.append(
                IssueCandidate(
                    candidateId=hit.ruleId,
                    title=self._titles.get(hit.ruleId, hit.ruleId),
                    ruleHits=[hit],
                    layerHint=hit.layerHint,
                    severityHint=hit.severityHint,
                    findingType=finding_type,
                    docEvidence=doc_evidence,
                    policyEvidence=policy_evidence,
                    evidenceMissing=evidence_missing,
                    manualReviewNeeded=manual_review_needed,
                    manualReviewReason=self._resolve_manual_review_reason(
                        rule_id=hit.ruleId,
                        manual_review_needed=manual_review_needed,
                        evidence_missing=evidence_missing,
                        doc_evidence=doc_evidence,
                        applicability_state=hit.applicabilityState,
                        blocking_reasons=blocking_reasons,
                    ),
                    missingFactKeys=list(hit.missingFactKeys),
                    blockingReasons=list(dict.fromkeys(blocking_reasons)),
                )
            )
        return candidates

    def _resolve_manual_review_reason(
        self,
        *,
        rule_id: str,
        manual_review_needed: bool,
        evidence_missing: bool,
        doc_evidence,
        applicability_state: str,
        blocking_reasons: list[str],
    ):
        if not manual_review_needed and applicability_state != 'blocked_by_visibility':
            return None
        if rule_id in self._manual_review_reasons:
            return self._manual_review_reasons[rule_id]
        if applicability_state == 'blocked_by_visibility':
            reason = self._resolve_visibility_reason(blocking_reasons=blocking_reasons, doc_evidence=doc_evidence)
            if reason:
                return reason
        visibilities = [span.visibility.value for span in doc_evidence if span.visibility is not None]
        if 'unknown' in visibilities:
            return 'visibility_unknown'
        if 'attachment_unparsed' in visibilities:
            return 'attachment_unparsed'
        if 'referenced_only' in visibilities:
            return 'referenced_only'
        if evidence_missing:
            return 'evidence_gap'
        return 'manual_confirmation_required'

    def _resolve_visibility_reason(self, *, blocking_reasons: list[str], doc_evidence) -> str | None:
        reasons = set(blocking_reasons)
        visibilities = {span.visibility.value for span in doc_evidence if span.visibility is not None}
        if {'parser_limited_pdf_requires_manual_review', 'parser_limited_source'} & reasons:
            return 'parser_limited_pdf_requires_manual_review'
        if 'unknown' in visibilities or {'visibility_unknown', 'attachment_unknown'} & reasons:
            return 'visibility_unknown'
        if 'attachment_unparsed' in visibilities or 'attachment_unparsed' in reasons:
            return 'attachment_unparsed'
        if 'referenced_only' in visibilities or 'referenced_only' in reasons:
            return 'referenced_only'
        if 'weak_section_structure_signal' in reasons:
            return 'weak_section_structure_signal'
        if 'visibility_gap' in reasons:
            return 'visibility_gap'
        return None

    def _is_closed_negative_hit(self, hit: RuleHit) -> bool:
        if hit.missingFactKeys:
            return False
        required_fact_keys = list(hit.requiredFactKeys or hit.factRefs or [])
        if not required_fact_keys:
            return False
        return all(self._is_closed_negative_fact_key(fact_key) for fact_key in required_fact_keys)

    def _is_closed_negative_fact_key(self, fact_key: str) -> bool:
        return fact_key.startswith(self._closed_negative_fact_prefixes) or fact_key in self._closed_negative_fact_keys

    def _collect_doc_evidence(self, fact_refs: list[str], facts: ExtractedFacts):
        evidence = []
        seen = set()
        for fact_ref in fact_refs:
            for span in facts.factEvidence.get(fact_ref, []):
                key = (
                    span.sourceId,
                    tuple(sorted(span.locator.model_dump(mode='json').items())),
                    span.excerpt,
                )
                if key in seen:
                    continue
                seen.add(key)
                evidence.append(span)
        return evidence

    def _annotate_evidence_spans(self, spans, *, gap_reason: str | None):
        if not gap_reason:
            return spans
        return [span.model_copy(update={'evidenceGapReason': span.evidenceGapReason or gap_reason}) for span in spans]

    def _derive_gap_reason(
        self,
        *,
        applicability_state: str,
        blocking_reasons: list[str],
        manual_review_needed: bool,
        evidence_missing: bool,
    ) -> str | None:
        if applicability_state == 'blocked_by_visibility':
            return self._resolve_visibility_reason(blocking_reasons=blocking_reasons, doc_evidence=[])
        if applicability_state == 'blocked_by_missing_fact' or evidence_missing:
            for reason in ['parser_limited_source', 'missing_fact', 'document_evidence_unavailable', 'policy_evidence_unavailable']:
                if reason in blocking_reasons:
                    return reason
            return 'missing_fact'
        if manual_review_needed:
            return 'manual_confirmation_required'
        return None
