from __future__ import annotations

from src.domain.models import ReviewLayer
from src.review.schema import ExtractedFacts, PolicyPack, RuleHit


class ReviewRuleEngine:
    def run(self, facts: ExtractedFacts, packs: list[PolicyPack], parse_result) -> list[RuleHit]:
        pack_by_rule: dict[str, str] = {}
        for pack in packs:
            for rule_id in pack.ruleIds:
                pack_by_rule.setdefault(rule_id, pack.id)

        hits: list[RuleHit] = []
        hits.extend(self._construction_org_hits(facts, pack_by_rule))
        hits.extend(self._hazardous_special_scheme_hits(facts, pack_by_rule))
        return hits

    def _construction_org_hits(self, facts: ExtractedFacts, pack_by_rule: dict[str, str]) -> list[RuleHit]:
        if 'construction_org_structure_completeness' not in pack_by_rule and 'construction_org.base' not in pack_by_rule.values():
            return []
        hits: list[RuleHit] = []
        section_presence = facts.projectFacts.get('sectionPresence') or {}
        missing_core_sections = [
            key
            for key in [
                'engineeringOverview',
                'constructionPlan',
                'schedulePlan',
                'resourcePlan',
                'safetyMeasures',
                'emergencyPlan',
                'layoutPlan',
            ]
            if not section_presence.get(key)
        ]
        hits.append(
            RuleHit(
                ruleId='construction_org_structure_completeness',
                packId=pack_by_rule.get('construction_org_structure_completeness', 'construction_org.base'),
                matchType='direct_hit',
                status='hit' if missing_core_sections else 'pass',
                layerHint=ReviewLayer.L1,
                severityHint='high' if len(missing_core_sections) >= 3 else 'medium',
                factRefs=[f'project.sectionPresence.{key}' for key in missing_core_sections] or ['project.sectionPresence.engineeringOverview'],
                evidenceRefs=['policy:construction_org_structure'],
                rationale='施工组织设计应覆盖工程概况、部署、进度、资源、安全、应急和平面布置等核心章节。',
            )
        )

        duplicate_sections = facts.projectFacts.get('duplicateSections') or []
        hits.append(
            RuleHit(
                ruleId='construction_org_duplicate_sections',
                packId=pack_by_rule.get('construction_org_duplicate_sections', 'construction_org.base'),
                matchType='direct_hit',
                status='hit' if duplicate_sections else 'pass',
                layerHint=ReviewLayer.L1,
                severityHint='medium',
                factRefs=['project.duplicateSections'],
                evidenceRefs=['policy:construction_org_structure'],
                rationale='章节标题重复会直接影响正式审查定位与条款挂接。',
            )
        )

        attachment_items = facts.attachmentFacts.get('attachments') or []
        attachment_gap = [item for item in attachment_items if item.get('visibility') != 'parsed']
        hits.append(
            RuleHit(
                ruleId='construction_org_attachment_visibility',
                packId=pack_by_rule.get('construction_org_attachment_visibility', 'construction_org.base'),
                matchType='visibility_gap',
                status='manual_review_needed' if attachment_gap else 'pass',
                layerHint=ReviewLayer.L1,
                severityHint='medium',
                factRefs=['attachments.visibility'],
                evidenceRefs=['policy:review_visibility_gap'],
                rationale='附件当前可视域不足时，应先标注人工复核，而不是直接判定缺失。',
            )
        )

        high_risk_categories = facts.hazardFacts.get('highRiskCategories') or []
        special_scheme_status = facts.hazardFacts.get('specialSchemePlanStatus')
        requires_special_scheme = bool(high_risk_categories and any(tag in high_risk_categories for tag in ['lifting_operations', 'temporary_power', 'hot_work']))
        if requires_special_scheme and special_scheme_status == 'explicit_section':
            special_scheme_result = 'pass'
        elif requires_special_scheme and special_scheme_status == 'generic_mention_only':
            special_scheme_result = 'manual_review_needed'
        elif requires_special_scheme:
            special_scheme_result = 'hit'
        else:
            special_scheme_result = 'not_applicable'
        hits.append(
            RuleHit(
                ruleId='construction_org_special_scheme_gap',
                packId=pack_by_rule.get('construction_org_special_scheme_gap', 'construction_org.base'),
                matchType='direct_hit',
                status=special_scheme_result,
                layerHint=ReviewLayer.L1,
                severityHint='high',
                factRefs=['hazard.highRiskCategories', 'hazard.specialSchemePlanStatus'],
                evidenceRefs=['policy:dangerous_special_scheme'],
                rationale='识别到危大/高风险作业后，需检查专项方案是否明确挂接到正文或附件。',
            )
        )

        emergency_plan_count = facts.emergencyFacts.get('targetedPlanCount') or 0
        emergency_status = 'pass' if emergency_plan_count >= 2 else ('hit' if high_risk_categories else 'not_applicable')
        hits.append(
            RuleHit(
                ruleId='construction_org_emergency_plan_targeted',
                packId=pack_by_rule.get('construction_org_emergency_plan_targeted', 'construction_org.base'),
                matchType='direct_hit',
                status=emergency_status,
                layerHint=ReviewLayer.L2,
                severityHint='medium',
                factRefs=['emergency.planTitles'],
                evidenceRefs=['policy:emergency_plan_targeted'],
                rationale='应急预案应与主要风险类别形成针对性映射。',
            )
        )

        shutdown_days = facts.scheduleFacts.get('shutdownWindowDays')
        labor_total = facts.resourceFacts.get('laborTotal')
        inferred_risk = bool(shutdown_days and labor_total and shutdown_days <= 7 and labor_total >= 35 and len(high_risk_categories) >= 3)
        hits.append(
            RuleHit(
                ruleId='construction_org_shutdown_resource_conflict',
                packId=pack_by_rule.get('construction_org_shutdown_resource_conflict', 'construction_org.base'),
                matchType='inferred_risk',
                status='hit' if inferred_risk else 'pass',
                layerHint=ReviewLayer.L3,
                severityHint='medium',
                factRefs=['schedule.shutdownWindowDays', 'resource.laborTotal', 'hazard.highRiskCategories'],
                evidenceRefs=['policy:construction_org_schedule_resource'],
                rationale='停机窗口紧、投入人力高且高风险工种并行时，需提示现场组织与交叉作业压力。',
            )
        )
        return hits

    def _hazardous_special_scheme_hits(self, facts: ExtractedFacts, pack_by_rule: dict[str, str]) -> list[RuleHit]:
        if 'hazardous_special_scheme_core_sections' not in pack_by_rule and 'hazardous_special_scheme.base' not in pack_by_rule.values():
            return []
        hits: list[RuleHit] = []
        section_presence = facts.projectFacts.get('sectionPresence') or {}
        missing_core_sections = [
            key
            for key in ['engineeringOverview', 'preparationBasis', 'constructionPlan', 'processMethod', 'safetyMeasures', 'emergencyPlan', 'calculationBook']
            if not section_presence.get(key)
        ]
        hits.append(
            RuleHit(
                ruleId='hazardous_special_scheme_core_sections',
                packId=pack_by_rule.get('hazardous_special_scheme_core_sections', 'hazardous_special_scheme.base'),
                matchType='direct_hit',
                status='hit' if missing_core_sections else 'pass',
                layerHint=ReviewLayer.L1,
                severityHint='high',
                factRefs=[f'project.sectionPresence.{key}' for key in missing_core_sections] or ['project.sectionPresence.engineeringOverview'],
                evidenceRefs=['policy:hazardous_scheme_structure'],
                rationale='危大专项方案应包含核心章节，以支撑正式审查和现场执行。',
            )
        )

        attachment_items = facts.attachmentFacts.get('attachments') or []
        attachment_gap = [item for item in attachment_items if item.get('visibility') != 'parsed']
        hits.append(
            RuleHit(
                ruleId='hazardous_special_scheme_attachment_visibility',
                packId=pack_by_rule.get('hazardous_special_scheme_attachment_visibility', 'hazardous_special_scheme.base'),
                matchType='visibility_gap',
                status='manual_review_needed' if attachment_gap else 'pass',
                layerHint=ReviewLayer.L1,
                severityHint='medium',
                factRefs=['attachments.visibility'],
                evidenceRefs=['policy:review_visibility_gap'],
                rationale='专项方案附件/图纸不在可视域内时，只能标为人工复核。',
            )
        )

        has_lifting = bool(facts.hazardFacts.get('liftingOperation'))
        calc_present = bool(facts.hazardFacts.get('calculationEvidencePresent'))
        calc_status = 'pass' if (not has_lifting or calc_present) else 'hit'
        hits.append(
            RuleHit(
                ruleId='hazardous_special_scheme_calculation_evidence',
                packId=pack_by_rule.get('hazardous_special_scheme_calculation_evidence', 'hazardous_special_scheme.base'),
                matchType='direct_hit',
                status=calc_status,
                layerHint=ReviewLayer.L2,
                severityHint='high',
                factRefs=['hazard.liftingOperation', 'hazard.calculationEvidencePresent', 'hazard.craneCapacityTon', 'hazard.calculatedLiftWeightTon'],
                evidenceRefs=['policy:hazardous_scheme_calculation'],
                rationale='涉及吊装或受力稳定时，应形成可追溯验算依据。',
            )
        )

        emergency_plan_count = facts.emergencyFacts.get('targetedPlanCount') or 0
        emergency_status = 'pass' if emergency_plan_count >= 1 else ('hit' if facts.hazardFacts.get('highRiskCategories') else 'not_applicable')
        hits.append(
            RuleHit(
                ruleId='hazardous_special_scheme_emergency_targeted',
                packId=pack_by_rule.get('hazardous_special_scheme_emergency_targeted', 'hazardous_special_scheme.base'),
                matchType='direct_hit',
                status=emergency_status,
                layerHint=ReviewLayer.L2,
                severityHint='medium',
                factRefs=['emergency.planTitles'],
                evidenceRefs=['policy:emergency_plan_targeted'],
                rationale='专项方案应形成与主要危险源匹配的应急处置安排。',
            )
        )

        measure_status = 'pass' if facts.hazardFacts.get('measureSectionPresent') and facts.hazardFacts.get('monitoringSectionPresent') else ('hit' if facts.hazardFacts.get('highRiskCategories') else 'not_applicable')
        hits.append(
            RuleHit(
                ruleId='hazardous_special_scheme_measure_linkage',
                packId=pack_by_rule.get('hazardous_special_scheme_measure_linkage', 'hazardous_special_scheme.base'),
                matchType='inferred_risk',
                status=measure_status,
                layerHint=ReviewLayer.L3,
                severityHint='medium',
                factRefs=['hazard.highRiskCategories', 'hazard.measureSectionPresent', 'hazard.monitoringSectionPresent'],
                evidenceRefs=['policy:hazardous_scheme_measures'],
                rationale='主要危险源、控制措施与监测监控应形成闭环，否则现场执行风险较高。',
            )
        )
        return hits
