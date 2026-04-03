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
            'hazardous_special_scheme_core_sections': '危大专项方案核心章节不完整',
            'hazardous_special_scheme_attachment_visibility': '专项方案附件处于可视域缺口，需人工复核原件',
            'hazardous_special_scheme_calculation_evidence': '专项方案缺少可追溯验算依据',
            'hazardous_special_scheme_emergency_targeted': '专项方案应急处置安排针对性不足',
            'hazardous_special_scheme_measure_linkage': '主要危险源、控制措施与监测监控闭环不足',
        }
        self._finding_types = {
            'construction_org_structure_completeness': FindingType.hard_evidence,
            'construction_org_duplicate_sections': FindingType.hard_evidence,
            'construction_org_attachment_visibility': FindingType.visibility_gap,
            'construction_org_special_scheme_gap': FindingType.hard_evidence,
            'construction_org_emergency_plan_targeted': FindingType.hard_evidence,
            'construction_org_shutdown_resource_conflict': FindingType.engineering_inference,
            'hazardous_special_scheme_core_sections': FindingType.hard_evidence,
            'hazardous_special_scheme_attachment_visibility': FindingType.visibility_gap,
            'hazardous_special_scheme_calculation_evidence': FindingType.hard_evidence,
            'hazardous_special_scheme_emergency_targeted': FindingType.hard_evidence,
            'hazardous_special_scheme_measure_linkage': FindingType.engineering_inference,
        }
        self._manual_review_reasons = {
            'construction_org_attachment_visibility': 'visibility_gap',
            'hazardous_special_scheme_attachment_visibility': 'visibility_gap',
            'construction_org_special_scheme_gap': 'special_scheme_reference_requires_manual_confirmation',
        }

    def build(self, rule_hits: list[RuleHit], facts: ExtractedFacts, parse_result, packs) -> list[IssueCandidate]:
        candidates: list[IssueCandidate] = []
        selected_pack_ids = [pack.id for pack in packs]
        for hit in rule_hits:
            if hit.status not in {'hit', 'manual_review_needed'}:
                continue
            doc_evidence = self._collect_doc_evidence(hit.factRefs, facts)
            policy_evidence = self.clause_store.get_policy_evidence(hit.ruleId, selected_pack_ids)
            visibility_gap = any(span.visibility and span.visibility.value != 'parsed' for span in doc_evidence)
            manual_review_needed = hit.status == 'manual_review_needed' or visibility_gap
            evidence_missing = not doc_evidence or not policy_evidence
            candidates.append(
                IssueCandidate(
                    candidateId=hit.ruleId,
                    title=self._titles.get(hit.ruleId, hit.ruleId),
                    ruleHits=[hit],
                    layerHint=hit.layerHint,
                    severityHint=hit.severityHint,
                    findingType=self._finding_types.get(hit.ruleId, FindingType.hard_evidence),
                    docEvidence=doc_evidence,
                    policyEvidence=policy_evidence,
                    evidenceMissing=evidence_missing,
                    manualReviewNeeded=manual_review_needed,
                    manualReviewReason=self._resolve_manual_review_reason(
                        rule_id=hit.ruleId,
                        manual_review_needed=manual_review_needed,
                        evidence_missing=evidence_missing,
                        doc_evidence=doc_evidence,
                    ),
                )
            )
        return candidates

    def _resolve_manual_review_reason(self, *, rule_id: str, manual_review_needed: bool, evidence_missing: bool, doc_evidence):
        if not manual_review_needed:
            return None
        if rule_id in self._manual_review_reasons:
            return self._manual_review_reasons[rule_id]
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
