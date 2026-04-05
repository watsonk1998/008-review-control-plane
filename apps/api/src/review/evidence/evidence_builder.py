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
            'hazardous_special_scheme_attachment_visibility': '专项方案附件处于可视域缺口，需人工复核原件',
            'hazardous_special_scheme_calculation_evidence': '专项方案缺少可追溯验算依据',
            'hazardous_special_scheme_emergency_targeted': '专项方案应急处置安排针对性不足',
            'hazardous_special_scheme_measure_linkage': '主要危险源、控制措施与监测监控闭环不足',
            'supervision_plan_structure_completeness': '监理规划核心章节不完整',
            'supervision_plan_monitoring_linkage': '监理规划缺少明确的监测监控/旁站安排',
            'supervision_plan_attachment_visibility': '监理规划附件处于可视域缺口，需人工复核原件',
            'review_support_material_context_only': '审查支持材料不能替代正式方案正文',
            'review_support_material_attachment_visibility': '审查支持材料附件处于可视域缺口，需人工复核原件',
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
            'hazardous_special_scheme_attachment_visibility': FindingType.visibility_gap,
            'hazardous_special_scheme_calculation_evidence': FindingType.hard_evidence,
            'hazardous_special_scheme_emergency_targeted': FindingType.hard_evidence,
            'hazardous_special_scheme_measure_linkage': FindingType.engineering_inference,
            'supervision_plan_structure_completeness': FindingType.hard_evidence,
            'supervision_plan_monitoring_linkage': FindingType.hard_evidence,
            'supervision_plan_attachment_visibility': FindingType.visibility_gap,
            'review_support_material_context_only': FindingType.suggestion_enhancement,
            'review_support_material_attachment_visibility': FindingType.visibility_gap,
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
            'supervision_plan_attachment_visibility': 'visibility_gap',
            'review_support_material_attachment_visibility': 'visibility_gap',
            'construction_org_special_scheme_gap': 'special_scheme_reference_requires_manual_confirmation',
            'lifting_operations_special_scheme_linkage': 'special_scheme_reference_requires_manual_confirmation',
        }
        self._closed_negative_fact_prefixes = ('project.sectionPresence.',)
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
