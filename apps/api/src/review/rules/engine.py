from __future__ import annotations

from src.domain.models import ReviewLayer
from src.review.schema import ExtractedFacts, PolicyPack, RuleHit


class ReviewRuleEngine:
    def run(self, facts: ExtractedFacts, packs: list[PolicyPack], parse_result) -> list[RuleHit]:
        pack_by_rule: dict[str, tuple[str, str]] = {}
        selected_pack_ids = {pack.id for pack in packs}
        for pack in packs:
            for rule_id in pack.ruleIds:
                pack_by_rule.setdefault(rule_id, (pack.id, pack.readiness))

        hits: list[RuleHit] = []
        hits.extend(self._construction_org_hits(facts, pack_by_rule))
        hits.extend(self._construction_scheme_hits(facts, pack_by_rule))
        hits.extend(self._hazardous_special_scheme_hits(facts, pack_by_rule))
        hits.extend(self._supervision_plan_hits(facts, pack_by_rule))
        hits.extend(self._review_support_material_hits(facts, pack_by_rule))
        hits.extend(self._lifting_operations_hits(facts, pack_by_rule, selected_pack_ids))
        hits.extend(self._temporary_power_hits(facts, pack_by_rule, selected_pack_ids))
        hits.extend(self._hot_work_hits(facts, pack_by_rule, selected_pack_ids))
        hits.extend(self._gas_area_ops_hits(facts, pack_by_rule, selected_pack_ids))
        return hits

    def _construction_org_hits(self, facts: ExtractedFacts, pack_by_rule: dict[str, tuple[str, str]]) -> list[RuleHit]:
        if 'construction_org_structure_completeness' not in pack_by_rule and not any(pack_id == 'construction_org.base' for pack_id, _ in pack_by_rule.values()):
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
        base_pack_id, base_pack_readiness = pack_by_rule.get('construction_org_structure_completeness', ('construction_org.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='construction_org_structure_completeness',
                packId=base_pack_id,
                packReadiness=base_pack_readiness,
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
        duplicate_pack_id, duplicate_pack_readiness = pack_by_rule.get('construction_org_duplicate_sections', ('construction_org.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='construction_org_duplicate_sections',
                packId=duplicate_pack_id,
                packReadiness=duplicate_pack_readiness,
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
        attachment_pack_id, attachment_pack_readiness = pack_by_rule.get('construction_org_attachment_visibility', ('construction_org.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='construction_org_attachment_visibility',
                packId=attachment_pack_id,
                packReadiness=attachment_pack_readiness,
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
        special_pack_id, special_pack_readiness = pack_by_rule.get('construction_org_special_scheme_gap', ('construction_org.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='construction_org_special_scheme_gap',
                packId=special_pack_id,
                packReadiness=special_pack_readiness,
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
        emergency_pack_id, emergency_pack_readiness = pack_by_rule.get('construction_org_emergency_plan_targeted', ('construction_org.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='construction_org_emergency_plan_targeted',
                packId=emergency_pack_id,
                packReadiness=emergency_pack_readiness,
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
        resource_pack_id, resource_pack_readiness = pack_by_rule.get('construction_org_shutdown_resource_conflict', ('construction_org.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='construction_org_shutdown_resource_conflict',
                packId=resource_pack_id,
                packReadiness=resource_pack_readiness,
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

    def _construction_scheme_hits(self, facts: ExtractedFacts, pack_by_rule: dict[str, tuple[str, str]]) -> list[RuleHit]:
        if not any(pack_id == 'construction_scheme.base' for pack_id, _ in pack_by_rule.values()):
            return []
        hits: list[RuleHit] = []
        section_presence = facts.projectFacts.get('sectionPresence') or {}
        missing_core_sections = [
            key
            for key in ['engineeringOverview', 'preparationBasis', 'processMethod', 'safetyMeasures']
            if not section_presence.get(key)
        ]
        pack_id, pack_readiness = pack_by_rule.get('construction_scheme_structure_completeness', ('construction_scheme.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='construction_scheme_structure_completeness',
                packId=pack_id,
                packReadiness=pack_readiness,
                matchType='direct_hit',
                status='hit' if missing_core_sections else 'pass',
                layerHint=ReviewLayer.L1,
                severityHint='high' if len(missing_core_sections) >= 2 else 'medium',
                factRefs=[f'project.sectionPresence.{key}' for key in missing_core_sections] or ['project.sectionPresence.engineeringOverview'],
                evidenceRefs=['policy:construction_scheme_structure'],
                rationale='一般施工方案至少应覆盖工程概况、编制依据、施工方法和安全措施等最小核心章节。',
            )
        )

        attachment_items = facts.attachmentFacts.get('attachments') or []
        attachment_gap = [item for item in attachment_items if item.get('visibility') != 'parsed']
        attachment_pack_id, attachment_pack_readiness = pack_by_rule.get('construction_scheme_attachment_visibility', ('construction_scheme.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='construction_scheme_attachment_visibility',
                packId=attachment_pack_id,
                packReadiness=attachment_pack_readiness,
                matchType='visibility_gap',
                status='manual_review_needed' if attachment_gap else 'pass',
                layerHint=ReviewLayer.L1,
                severityHint='medium',
                factRefs=['attachments.visibility'],
                evidenceRefs=['policy:review_visibility_gap'],
                rationale='施工方案附件未进入当前可视域时，应先标记人工复核。',
            )
        )
        return hits

    def _hazardous_special_scheme_hits(self, facts: ExtractedFacts, pack_by_rule: dict[str, tuple[str, str]]) -> list[RuleHit]:
        if 'hazardous_special_scheme_core_sections' not in pack_by_rule and not any(pack_id == 'hazardous_special_scheme.base' for pack_id, _ in pack_by_rule.values()):
            return []
        hits: list[RuleHit] = []
        section_presence = facts.projectFacts.get('sectionPresence') or {}
        missing_core_sections = [
            key
            for key in ['engineeringOverview', 'preparationBasis', 'constructionPlan', 'processMethod', 'safetyMeasures', 'emergencyPlan', 'calculationBook']
            if not section_presence.get(key)
        ]
        core_pack_id, core_pack_readiness = pack_by_rule.get('hazardous_special_scheme_core_sections', ('hazardous_special_scheme.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='hazardous_special_scheme_core_sections',
                packId=core_pack_id,
                packReadiness=core_pack_readiness,
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
        hz_attachment_pack_id, hz_attachment_pack_readiness = pack_by_rule.get('hazardous_special_scheme_attachment_visibility', ('hazardous_special_scheme.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='hazardous_special_scheme_attachment_visibility',
                packId=hz_attachment_pack_id,
                packReadiness=hz_attachment_pack_readiness,
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
        calc_pack_id, calc_pack_readiness = pack_by_rule.get('hazardous_special_scheme_calculation_evidence', ('hazardous_special_scheme.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='hazardous_special_scheme_calculation_evidence',
                packId=calc_pack_id,
                packReadiness=calc_pack_readiness,
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
        hz_emergency_pack_id, hz_emergency_pack_readiness = pack_by_rule.get('hazardous_special_scheme_emergency_targeted', ('hazardous_special_scheme.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='hazardous_special_scheme_emergency_targeted',
                packId=hz_emergency_pack_id,
                packReadiness=hz_emergency_pack_readiness,
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
        measure_pack_id, measure_pack_readiness = pack_by_rule.get('hazardous_special_scheme_measure_linkage', ('hazardous_special_scheme.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='hazardous_special_scheme_measure_linkage',
                packId=measure_pack_id,
                packReadiness=measure_pack_readiness,
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

    def _supervision_plan_hits(self, facts: ExtractedFacts, pack_by_rule: dict[str, tuple[str, str]]) -> list[RuleHit]:
        if not any(pack_id == 'supervision_plan.base' for pack_id, _ in pack_by_rule.values()):
            return []
        hits: list[RuleHit] = []
        section_presence = facts.projectFacts.get('sectionPresence') or {}
        missing_core_sections = [
            key
            for key in ['engineeringOverview', 'preparationBasis', 'safetyMeasures']
            if not section_presence.get(key)
        ]
        structure_pack_id, structure_pack_readiness = pack_by_rule.get('supervision_plan_structure_completeness', ('supervision_plan.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='supervision_plan_structure_completeness',
                packId=structure_pack_id,
                packReadiness=structure_pack_readiness,
                matchType='direct_hit',
                status='hit' if missing_core_sections else 'pass',
                layerHint=ReviewLayer.L1,
                severityHint='medium',
                factRefs=[f'project.sectionPresence.{key}' for key in missing_core_sections] or ['project.sectionPresence.engineeringOverview'],
                evidenceRefs=['policy:supervision_plan_structure'],
                rationale='监理规划至少应提供工程概况、编制依据和监理控制措施的基础结构。',
            )
        )

        monitoring_present = bool(section_presence.get('monitoringPlan'))
        monitoring_pack_id, monitoring_pack_readiness = pack_by_rule.get('supervision_plan_monitoring_linkage', ('supervision_plan.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='supervision_plan_monitoring_linkage',
                packId=monitoring_pack_id,
                packReadiness=monitoring_pack_readiness,
                matchType='direct_hit',
                status='pass' if monitoring_present else 'hit',
                layerHint=ReviewLayer.L2,
                severityHint='medium',
                factRefs=['project.sectionPresence.monitoringPlan'],
                evidenceRefs=['policy:supervision_plan_monitoring'],
                rationale='监理规划应明确监测监控、旁站或巡视控制安排。',
            )
        )

        attachment_items = facts.attachmentFacts.get('attachments') or []
        attachment_gap = [item for item in attachment_items if item.get('visibility') != 'parsed']
        attachment_pack_id, attachment_pack_readiness = pack_by_rule.get('supervision_plan_attachment_visibility', ('supervision_plan.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='supervision_plan_attachment_visibility',
                packId=attachment_pack_id,
                packReadiness=attachment_pack_readiness,
                matchType='visibility_gap',
                status='manual_review_needed' if attachment_gap else 'pass',
                layerHint=ReviewLayer.L1,
                severityHint='medium',
                factRefs=['attachments.visibility'],
                evidenceRefs=['policy:review_visibility_gap'],
                rationale='监理规划附件不可视时，应先进入人工复核而不是直接判断缺失。',
            )
        )
        return hits

    def _review_support_material_hits(self, facts: ExtractedFacts, pack_by_rule: dict[str, tuple[str, str]]) -> list[RuleHit]:
        if not any(pack_id == 'review_support_material.base' for pack_id, _ in pack_by_rule.values()):
            return []
        hits: list[RuleHit] = []
        context_only = bool(facts.projectFacts.get('contextOnly'))
        pack_id, pack_readiness = pack_by_rule.get('review_support_material_context_only', ('review_support_material.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='review_support_material_context_only',
                packId=pack_id,
                packReadiness=pack_readiness,
                matchType='direct_hit',
                status='hit' if context_only else 'manual_review_needed',
                layerHint=ReviewLayer.L1,
                severityHint='low',
                factRefs=['project.contextOnly'],
                evidenceRefs=['policy:review_support_material_context'],
                rationale='审查支持材料只能补充背景或辅助判断，不能替代正式方案正文。',
            )
        )

        attachment_items = facts.attachmentFacts.get('attachments') or []
        attachment_gap = [item for item in attachment_items if item.get('visibility') != 'parsed']
        attachment_pack_id, attachment_pack_readiness = pack_by_rule.get('review_support_material_attachment_visibility', ('review_support_material.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='review_support_material_attachment_visibility',
                packId=attachment_pack_id,
                packReadiness=attachment_pack_readiness,
                matchType='visibility_gap',
                status='manual_review_needed' if attachment_gap else 'pass',
                layerHint=ReviewLayer.L1,
                severityHint='low',
                factRefs=['attachments.visibility'],
                evidenceRefs=['policy:review_visibility_gap'],
                rationale='支持材料附件不可视时仍需显式标记人工复核。',
            )
        )
        return hits

    def _lifting_operations_hits(
        self,
        facts: ExtractedFacts,
        pack_by_rule: dict[str, tuple[str, str]],
        selected_pack_ids: set[str],
    ) -> list[RuleHit]:
        if 'lifting_operations.base' not in selected_pack_ids:
            return []
        hits: list[RuleHit] = []
        if 'construction_org.base' in selected_pack_ids:
            special_scheme_status = facts.hazardFacts.get('specialSchemePlanStatus')
            if special_scheme_status == 'explicit_section':
                special_scheme_result = 'pass'
            elif special_scheme_status == 'generic_mention_only':
                special_scheme_result = 'manual_review_needed'
            else:
                special_scheme_result = 'hit'
            pack_id, pack_readiness = pack_by_rule.get('lifting_operations_special_scheme_linkage', ('lifting_operations.base', 'ready'))
            hits.append(
                RuleHit(
                    ruleId='lifting_operations_special_scheme_linkage',
                    packId=pack_id,
                    packReadiness=pack_readiness,
                    matchType='direct_hit',
                    status=special_scheme_result,
                    layerHint=ReviewLayer.L1,
                    severityHint='high',
                    factRefs=['hazard.liftingOperation', 'hazard.specialSchemePlanStatus'],
                    evidenceRefs=['policy:dangerous_special_scheme'],
                    rationale='起重吊装场景需明确专项方案/专项技术措施的正文挂接和适用边界。',
                )
            )
        if facts.hazardFacts.get('liftingOperation'):
            calc_present = bool(facts.hazardFacts.get('calculationEvidencePresent'))
            pack_id, pack_readiness = pack_by_rule.get('lifting_operations_calculation_traceability', ('lifting_operations.base', 'ready'))
            hits.append(
                RuleHit(
                    ruleId='lifting_operations_calculation_traceability',
                    packId=pack_id,
                    packReadiness=pack_readiness,
                    matchType='direct_hit',
                    status='pass' if calc_present else 'hit',
                    layerHint=ReviewLayer.L2,
                    severityHint='high',
                    factRefs=['hazard.liftingOperation', 'hazard.calculationEvidencePresent', 'hazard.craneCapacityTon', 'hazard.calculatedLiftWeightTon'],
                    evidenceRefs=['policy:hazardous_scheme_calculation'],
                    rationale='起重吊装至少应有设备参数、起重量或验算依据可追溯。',
                )
            )
        return hits

    def _temporary_power_hits(
        self,
        facts: ExtractedFacts,
        pack_by_rule: dict[str, tuple[str, str]],
        selected_pack_ids: set[str],
    ) -> list[RuleHit]:
        if 'temporary_power.base' not in selected_pack_ids or not ({'construction_org.base', 'construction_scheme.base'} & selected_pack_ids):
            return []
        if not facts.hazardFacts.get('temporaryPower'):
            return []
        targeted_titles = facts.emergencyFacts.get('planTitles') or []
        has_power_title = self._contains_keywords(targeted_titles, ('触电', '停送电', '临电', '用电'))
        measures_ready = bool(facts.hazardFacts.get('measureSectionPresent'))
        monitoring_ready = bool(facts.hazardFacts.get('monitoringSectionPresent'))
        status = 'pass' if measures_ready and monitoring_ready and has_power_title else 'hit'
        pack_id, pack_readiness = pack_by_rule.get('temporary_power_control_linkage', ('temporary_power.base', 'ready'))
        return [
            RuleHit(
                ruleId='temporary_power_control_linkage',
                packId=pack_id,
                packReadiness=pack_readiness,
                matchType='inferred_risk',
                status=status,
                layerHint=ReviewLayer.L2,
                severityHint='medium',
                factRefs=['hazard.temporaryPower', 'hazard.measureSectionPresent', 'hazard.monitoringSectionPresent', 'emergency.planTitles'],
                evidenceRefs=['policy:hazardous_scheme_measures', 'policy:emergency_plan_targeted'],
                rationale='临时用电/停送电作业应同时落到控制措施、监测监控和触电类应急处置。',
            )
        ]

    def _hot_work_hits(
        self,
        facts: ExtractedFacts,
        pack_by_rule: dict[str, tuple[str, str]],
        selected_pack_ids: set[str],
    ) -> list[RuleHit]:
        if 'hot_work.base' not in selected_pack_ids or not ({'construction_org.base', 'construction_scheme.base'} & selected_pack_ids):
            return []
        if not facts.hazardFacts.get('hotWork'):
            return []
        targeted_titles = facts.emergencyFacts.get('planTitles') or []
        has_fire_title = self._contains_keywords(targeted_titles, ('火灾', '动火', '爆燃', '爆炸'))
        status = 'pass' if has_fire_title else 'hit'
        pack_id, pack_readiness = pack_by_rule.get('hot_work_emergency_targeted', ('hot_work.base', 'ready'))
        return [
            RuleHit(
                ruleId='hot_work_emergency_targeted',
                packId=pack_id,
                packReadiness=pack_readiness,
                matchType='direct_hit',
                status=status,
                layerHint=ReviewLayer.L2,
                severityHint='medium',
                factRefs=['hazard.hotWork', 'emergency.planTitles'],
                evidenceRefs=['policy:emergency_plan_targeted'],
                rationale='动火场景至少应看到火灾/爆燃类应急处置标题或明确联动安排。',
            )
        ]

    def _gas_area_ops_hits(
        self,
        facts: ExtractedFacts,
        pack_by_rule: dict[str, tuple[str, str]],
        selected_pack_ids: set[str],
    ) -> list[RuleHit]:
        if 'gas_area_ops.base' not in selected_pack_ids:
            return []
        if not facts.hazardFacts.get('gasArea'):
            return []
        targeted_titles = facts.emergencyFacts.get('planTitles') or []
        has_targeted_title = self._contains_keywords(targeted_titles, ('煤气', '中毒', '窒息', '爆炸', '泄漏'))
        measures_ready = bool(facts.hazardFacts.get('measureSectionPresent'))
        monitoring_ready = bool(facts.hazardFacts.get('monitoringSectionPresent'))
        status = 'pass' if measures_ready and monitoring_ready and has_targeted_title else 'hit'
        pack_id, pack_readiness = pack_by_rule.get('gas_area_ops_control_linkage', ('gas_area_ops.base', 'ready'))
        return [
            RuleHit(
                ruleId='gas_area_ops_control_linkage',
                packId=pack_id,
                packReadiness=pack_readiness,
                matchType='inferred_risk',
                status=status,
                layerHint=ReviewLayer.L2,
                severityHint='high',
                factRefs=['hazard.gasArea', 'hazard.measureSectionPresent', 'hazard.monitoringSectionPresent', 'emergency.planTitles'],
                evidenceRefs=['policy:hazardous_scheme_measures', 'policy:emergency_plan_targeted'],
                rationale='煤气区域作业至少应形成控制措施、监测监控与中毒/窒息/爆炸类应急处置的同链表达。',
            )
        ]

    def _contains_keywords(self, values: list[str], keywords: tuple[str, ...]) -> bool:
        return any(any(keyword in str(value) for keyword in keywords) for value in values)
