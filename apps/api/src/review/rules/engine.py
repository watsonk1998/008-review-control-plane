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
        hits.extend(self._foundation_pit_hits(facts, pack_by_rule, selected_pack_ids))
        hits.extend(self._formwork_support_hits(facts, pack_by_rule, selected_pack_ids))
        hits.extend(self._lifting_installation_removal_hits(facts, pack_by_rule, selected_pack_ids))
        hits.extend(self._scaffold_hits(facts, pack_by_rule, selected_pack_ids))
        hits.extend(self._demolition_hits(facts, pack_by_rule, selected_pack_ids))
        hits.extend(self._underground_excavation_hits(facts, pack_by_rule, selected_pack_ids))
        hits.extend(self._curtain_wall_installation_hits(facts, pack_by_rule, selected_pack_ids))
        hits.extend(self._manual_bored_pile_hits(facts, pack_by_rule, selected_pack_ids))
        hits.extend(self._steel_structure_installation_hits(facts, pack_by_rule, selected_pack_ids))
        hits.extend(self._temporary_power_hits(facts, pack_by_rule, selected_pack_ids))
        hits.extend(self._hot_work_hits(facts, pack_by_rule, selected_pack_ids))
        hits.extend(self._gas_area_ops_hits(facts, pack_by_rule, selected_pack_ids))
        return hits

    def _construction_org_hits(self, facts: ExtractedFacts, pack_by_rule: dict[str, tuple[str, str]]) -> list[RuleHit]:
        if 'construction_org_structure_completeness' not in pack_by_rule and not any(pack_id == 'construction_org.base' for pack_id, _ in pack_by_rule.values()):
            return []
        hits: list[RuleHit] = []
        structure_rows = facts.projectFacts.get('structureCompleteness') or []
        deficient_rows = [row for row in structure_rows if row.get('status') in {'missing', 'partial'}]
        blocked_rows = [row for row in structure_rows if row.get('status') == 'blocked_by_visibility']
        deficient_fact_keys = [f'project.structureCompleteness.{row["itemKey"]}' for row in [*deficient_rows, *blocked_rows]]
        missing_hard_rows = [row for row in deficient_rows if row.get('status') == 'missing']
        base_pack_id, base_pack_readiness = pack_by_rule.get('construction_org_structure_completeness', ('construction_org.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='construction_org_structure_completeness',
                packId=base_pack_id,
                packReadiness=base_pack_readiness,
                matchType='direct_hit',
                status='hit' if deficient_rows or blocked_rows else 'pass',
                layerHint=ReviewLayer.L1,
                severityHint='high' if len(missing_hard_rows) >= 2 else 'medium',
                factRefs=deficient_fact_keys or ['project.structureCompleteness.engineeringOverview'],
                evidenceRefs=['policy:construction_org_structure'],
                rationale='施工组织设计的结构完整性应按 GB/T 50502-2009 的 12 项主干要求逐项核对。',
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
            for key in [
                'engineeringOverview',
                'preparationBasis',
                'constructionPlan',
                'processMethod',
                'safetyMeasures',
                'emergencyPlan',
                'calculationBook',
                'staffingAndRoles',
                'acceptanceRequirements',
                'riskIdentification',
                'siteLayout',
                'surroundingConditions',
                'participantResponsibilities',
            ]
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

        staffing_missing = not section_presence.get('staffingAndRoles')
        staffing_pack_id, staffing_pack_readiness = pack_by_rule.get('hazardous_special_scheme_staffing_completeness', ('hazardous_special_scheme.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='hazardous_special_scheme_staffing_completeness',
                packId=staffing_pack_id,
                packReadiness=staffing_pack_readiness,
                matchType='direct_hit',
                status='hit' if staffing_missing else 'pass',
                layerHint=ReviewLayer.L1,
                severityHint='medium',
                factRefs=['project.sectionPresence.staffingAndRoles'],
                evidenceRefs=['policy:hazardous_scheme_structure'],
                rationale='危大专项方案应明确施工管理、专职安全和特种作业人员配备与分工。',
            )
        )

        acceptance_missing = not section_presence.get('acceptanceRequirements')
        acceptance_pack_id, acceptance_pack_readiness = pack_by_rule.get('hazardous_special_scheme_acceptance_completeness', ('hazardous_special_scheme.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='hazardous_special_scheme_acceptance_completeness',
                packId=acceptance_pack_id,
                packReadiness=acceptance_pack_readiness,
                matchType='direct_hit',
                status='hit' if acceptance_missing else 'pass',
                layerHint=ReviewLayer.L1,
                severityHint='medium',
                factRefs=['project.sectionPresence.acceptanceRequirements'],
                evidenceRefs=['policy:hazardous_scheme_structure'],
                rationale='危大专项方案应明确验收标准、程序、人员和关键验收内容。',
            )
        )

        drawing_pack_id, drawing_pack_readiness = pack_by_rule.get('hazardous_special_scheme_drawing_visibility', ('hazardous_special_scheme.base', 'ready'))
        drawing_present = bool(section_presence.get('drawingSet'))
        hits.append(
            RuleHit(
                ruleId='hazardous_special_scheme_drawing_visibility',
                packId=drawing_pack_id,
                packReadiness=drawing_pack_readiness,
                matchType='visibility_gap',
                status='manual_review_needed' if not drawing_present else 'pass',
                layerHint=ReviewLayer.L1,
                severityHint='medium',
                factRefs=['project.sectionPresence.drawingSet', 'attachments.visibility'],
                evidenceRefs=['policy:hazardous_scheme_drawings', 'policy:review_visibility_gap'],
                rationale='相关施工图纸、节点图和布置图首轮按可视域语义处理，缺口应进入人工复核。',
            )
        )

        risk_missing = not section_presence.get('riskIdentification')
        risk_pack_id, risk_pack_readiness = pack_by_rule.get('hazardous_special_scheme_risk_identification_completeness', ('hazardous_special_scheme.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='hazardous_special_scheme_risk_identification_completeness',
                packId=risk_pack_id,
                packReadiness=risk_pack_readiness,
                matchType='direct_hit',
                status='hit' if risk_missing else 'pass',
                layerHint=ReviewLayer.L1,
                severityHint='medium',
                factRefs=['project.sectionPresence.riskIdentification'],
                evidenceRefs=['policy:hazardous_scheme_structure'],
                rationale='危大专项方案应明确风险辨识与分级，形成后续控制与应急的前提。',
            )
        )

        layout_missing = [key for key in ['siteLayout', 'surroundingConditions'] if not section_presence.get(key)]
        layout_pack_id, layout_pack_readiness = pack_by_rule.get('hazardous_special_scheme_layout_and_environment_completeness', ('hazardous_special_scheme.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='hazardous_special_scheme_layout_and_environment_completeness',
                packId=layout_pack_id,
                packReadiness=layout_pack_readiness,
                matchType='direct_hit',
                status='hit' if layout_missing else 'pass',
                layerHint=ReviewLayer.L1,
                severityHint='medium',
                factRefs=[f'project.sectionPresence.{key}' for key in layout_missing] or ['project.sectionPresence.siteLayout'],
                evidenceRefs=['policy:hazardous_scheme_structure'],
                rationale='危大专项方案应覆盖施工平面布置和周边环境条件，便于审查作业边界和风险影响面。',
            )
        )
        return hits

    def _foundation_pit_hits(
        self,
        facts: ExtractedFacts,
        pack_by_rule: dict[str, tuple[str, str]],
        selected_pack_ids: set[str],
    ) -> list[RuleHit]:
        if 'foundation_pit.base' not in selected_pack_ids:
            return []
        hits: list[RuleHit] = []
        section_presence = facts.projectFacts.get('sectionPresence') or {}

        monitor_pack_id, monitor_pack_readiness = pack_by_rule.get('foundation_pit_monitoring_and_drawings', ('foundation_pit.base', 'ready'))
        needs_manual = not (section_presence.get('monitoringPlan') and section_presence.get('drawingSet'))
        hits.append(
            RuleHit(
                ruleId='foundation_pit_monitoring_and_drawings',
                packId=monitor_pack_id,
                packReadiness=monitor_pack_readiness,
                matchType='visibility_gap',
                status='manual_review_needed' if needs_manual else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='medium',
                factRefs=['project.sectionPresence.monitoringPlan', 'project.sectionPresence.drawingSet', 'attachments.visibility'],
                evidenceRefs=['policy:foundation_pit_monitoring'],
                rationale='基坑工程应有监测监控安排及相关图纸，图纸缺口首轮按人工复核处理。',
            )
        )

        sequence_pack_id, sequence_pack_readiness = pack_by_rule.get('foundation_pit_support_sequence_integrity', ('foundation_pit.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='foundation_pit_support_sequence_integrity',
                packId=sequence_pack_id,
                packReadiness=sequence_pack_readiness,
                matchType='direct_hit',
                status='hit' if not facts.projectFacts.get('foundationPitSupportSequencePresent') else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='high',
                factRefs=['project.foundationPitSupportSequencePresent', 'project.sectionPresence.processMethod'],
                evidenceRefs=['policy:foundation_pit_sequence'],
                rationale='基坑工程应明确支护、降水、土方开挖与加撑等关键关系链。',
            )
        )

        acceptance_pack_id, acceptance_pack_readiness = pack_by_rule.get('foundation_pit_acceptance_completeness', ('foundation_pit.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='foundation_pit_acceptance_completeness',
                packId=acceptance_pack_id,
                packReadiness=acceptance_pack_readiness,
                matchType='direct_hit',
                status='hit' if not section_presence.get('acceptanceRequirements') else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='medium',
                factRefs=['project.sectionPresence.acceptanceRequirements'],
                evidenceRefs=['policy:foundation_pit_acceptance'],
                rationale='基坑工程应明确位移、沉降、轴力和排水等关键验收控制内容。',
            )
        )
        return hits

    def _formwork_support_hits(
        self,
        facts: ExtractedFacts,
        pack_by_rule: dict[str, tuple[str, str]],
        selected_pack_ids: set[str],
    ) -> list[RuleHit]:
        if 'formwork_support.base' not in selected_pack_ids:
            return []
        hits: list[RuleHit] = []
        section_presence = facts.projectFacts.get('sectionPresence') or {}

        process_pack_id, process_pack_readiness = pack_by_rule.get('formwork_support_process_parameters', ('formwork_support.base', 'ready'))
        process_missing = not (section_presence.get('technicalParameters') and section_presence.get('processFlow') and facts.projectFacts.get('formworkPourSequencePresent'))
        hits.append(
            RuleHit(
                ruleId='formwork_support_process_parameters',
                packId=process_pack_id,
                packReadiness=process_pack_readiness,
                matchType='direct_hit',
                status='hit' if process_missing else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='high',
                factRefs=['project.sectionPresence.technicalParameters', 'project.sectionPresence.processFlow', 'project.formworkPourSequencePresent'],
                evidenceRefs=['policy:formwork_support_process'],
                rationale='模板支撑体系应明确技术参数、工艺流程及预压/浇筑顺序等关键过程要求。',
            )
        )

        calc_pack_id, calc_pack_readiness = pack_by_rule.get('formwork_support_calculation_traceability', ('formwork_support.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='formwork_support_calculation_traceability',
                packId=calc_pack_id,
                packReadiness=calc_pack_readiness,
                matchType='direct_hit',
                status='hit' if not section_presence.get('calculationBook') else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='high',
                factRefs=['project.sectionPresence.calculationBook'],
                evidenceRefs=['policy:formwork_support_calculation'],
                rationale='模板支撑体系应形成强度、刚度、稳定性及基础承载力等验算痕迹。',
            )
        )

        acceptance_pack_id, acceptance_pack_readiness = pack_by_rule.get('formwork_support_acceptance_completeness', ('formwork_support.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='formwork_support_acceptance_completeness',
                packId=acceptance_pack_id,
                packReadiness=acceptance_pack_readiness,
                matchType='direct_hit',
                status='hit' if not section_presence.get('acceptanceRequirements') else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='medium',
                factRefs=['project.sectionPresence.acceptanceRequirements'],
                evidenceRefs=['policy:formwork_support_acceptance'],
                rationale='模板支撑体系应明确阶段搭设质量、支撑构造和场地稳定性等验收内容。',
            )
        )
        return hits


    def _lifting_installation_removal_hits(
        self,
        facts: ExtractedFacts,
        pack_by_rule: dict[str, tuple[str, str]],
        selected_pack_ids: set[str],
    ) -> list[RuleHit]:
        if 'lifting_installation_removal.base' not in selected_pack_ids:
            return []
        hits: list[RuleHit] = []
        section_presence = facts.projectFacts.get('sectionPresence') or {}

        scheme_pack_id, scheme_pack_readiness = pack_by_rule.get('lifting_installation_removal_scheme_integrity', ('lifting_installation_removal.base', 'ready'))
        scheme_missing = not (
            section_presence.get('technicalParameters')
            and section_presence.get('processFlow')
            and section_presence.get('processMethod')
        )
        hits.append(
            RuleHit(
                ruleId='lifting_installation_removal_scheme_integrity',
                packId=scheme_pack_id,
                packReadiness=scheme_pack_readiness,
                matchType='direct_hit',
                status='hit' if scheme_missing else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='high',
                factRefs=['project.sectionPresence.technicalParameters', 'project.sectionPresence.processFlow', 'project.sectionPresence.processMethod'],
                evidenceRefs=['policy:lifting_installation_removal_scheme'],
                rationale='起重吊装及安装拆卸工程应明确设备参数、吊装流程和安装拆卸工艺。',
            )
        )

        bearing_pack_id, bearing_pack_readiness = pack_by_rule.get('lifting_installation_removal_site_bearing_traceability', ('lifting_installation_removal.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='lifting_installation_removal_site_bearing_traceability',
                packId=bearing_pack_id,
                packReadiness=bearing_pack_readiness,
                matchType='direct_hit',
                status='hit' if not facts.projectFacts.get('liftingSiteBearingPresent') else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='high',
                factRefs=['project.liftingSiteBearingPresent'],
                evidenceRefs=['policy:lifting_installation_removal_site_bearing'],
                rationale='起重吊装及安装拆卸工程应说明站位处地基或支承面的承载能力。',
            )
        )

        fixation_pack_id, fixation_pack_readiness = pack_by_rule.get('lifting_installation_removal_temporary_fixation_completeness', ('lifting_installation_removal.base', 'ready'))
        fixation_missing = not (
            facts.projectFacts.get('liftingTemporaryFixationPresent') and facts.projectFacts.get('liftingSupportDevicePresent')
        )
        hits.append(
            RuleHit(
                ruleId='lifting_installation_removal_temporary_fixation_completeness',
                packId=fixation_pack_id,
                packReadiness=fixation_pack_readiness,
                matchType='direct_hit',
                status='hit' if fixation_missing else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='high',
                factRefs=['project.liftingTemporaryFixationPresent', 'project.liftingSupportDevicePresent'],
                evidenceRefs=['policy:lifting_installation_removal_fixation'],
                rationale='起重吊装及安装拆卸工程应明确临时固定、缆风绳或辅助吊装装置等稳定措施。',
            )
        )

        drawing_pack_id, drawing_pack_readiness = pack_by_rule.get('lifting_installation_removal_drawing_visibility', ('lifting_installation_removal.base', 'ready'))
        drawing_gap = not section_presence.get('drawingSet')
        hits.append(
            RuleHit(
                ruleId='lifting_installation_removal_drawing_visibility',
                packId=drawing_pack_id,
                packReadiness=drawing_pack_readiness,
                matchType='visibility_gap',
                status='manual_review_needed' if drawing_gap else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='medium',
                factRefs=['project.sectionPresence.drawingSet', 'attachments.visibility'],
                evidenceRefs=['policy:lifting_installation_removal_drawings', 'policy:review_visibility_gap'],
                rationale='起重吊装及安装拆卸工程的站位图、平立面关系图等首轮按可视域优先语义处理。',
            )
        )
        return hits

    def _scaffold_hits(
        self,
        facts: ExtractedFacts,
        pack_by_rule: dict[str, tuple[str, str]],
        selected_pack_ids: set[str],
    ) -> list[RuleHit]:
        if 'scaffold.base' not in selected_pack_ids:
            return []
        hits: list[RuleHit] = []
        section_presence = facts.projectFacts.get('sectionPresence') or {}

        structure_pack_id, structure_pack_readiness = pack_by_rule.get('scaffold_structure_parameters_completeness', ('scaffold.base', 'ready'))
        structure_missing = not (section_presence.get('technicalParameters') and section_presence.get('processMethod'))
        hits.append(
            RuleHit(
                ruleId='scaffold_structure_parameters_completeness',
                packId=structure_pack_id,
                packReadiness=structure_pack_readiness,
                matchType='direct_hit',
                status='hit' if structure_missing else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='high',
                factRefs=['project.sectionPresence.technicalParameters', 'project.sectionPresence.processMethod'],
                evidenceRefs=['policy:scaffold_structure'],
                rationale='脚手架工程应明确架体类型、高度、基础和主要构造参数。',
            )
        )

        safety_pack_id, safety_pack_readiness = pack_by_rule.get('scaffold_safety_device_and_wall_tie_completeness', ('scaffold.base', 'ready'))
        safety_missing = not (facts.projectFacts.get('scaffoldWallTiePresent') and facts.projectFacts.get('scaffoldAntiFallPresent'))
        hits.append(
            RuleHit(
                ruleId='scaffold_safety_device_and_wall_tie_completeness',
                packId=safety_pack_id,
                packReadiness=safety_pack_readiness,
                matchType='direct_hit',
                status='hit' if safety_missing else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='high',
                factRefs=['project.scaffoldWallTiePresent', 'project.scaffoldAntiFallPresent'],
                evidenceRefs=['policy:scaffold_safety'],
                rationale='脚手架工程应明确连墙件、附着支撑和防倾覆/防坠落装置。',
            )
        )

        monitoring_pack_id, monitoring_pack_readiness = pack_by_rule.get('scaffold_monitoring_and_acceptance_completeness', ('scaffold.base', 'ready'))
        monitoring_missing = not (
            facts.projectFacts.get('scaffoldMonitoringPresent') and section_presence.get('acceptanceRequirements')
        )
        hits.append(
            RuleHit(
                ruleId='scaffold_monitoring_and_acceptance_completeness',
                packId=monitoring_pack_id,
                packReadiness=monitoring_pack_readiness,
                matchType='direct_hit',
                status='hit' if monitoring_missing else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='medium',
                factRefs=['project.scaffoldMonitoringPresent', 'project.sectionPresence.acceptanceRequirements'],
                evidenceRefs=['policy:scaffold_monitoring_acceptance'],
                rationale='脚手架工程应明确监测项目、控制值和关键验收内容。',
            )
        )
        return hits

    def _demolition_hits(
        self,
        facts: ExtractedFacts,
        pack_by_rule: dict[str, tuple[str, str]],
        selected_pack_ids: set[str],
    ) -> list[RuleHit]:
        if 'demolition.base' not in selected_pack_ids:
            return []
        hits: list[RuleHit] = []
        section_presence = facts.projectFacts.get('sectionPresence') or {}

        sequence_pack_id, sequence_pack_readiness = pack_by_rule.get('demolition_sequence_integrity', ('demolition.base', 'ready'))
        sequence_missing = not (facts.projectFacts.get('demolitionSequencePresent') and section_presence.get('processFlow'))
        hits.append(
            RuleHit(
                ruleId='demolition_sequence_integrity',
                packId=sequence_pack_id,
                packReadiness=sequence_pack_readiness,
                matchType='direct_hit',
                status='hit' if sequence_missing else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='high',
                factRefs=['project.demolitionSequencePresent', 'project.sectionPresence.processFlow'],
                evidenceRefs=['policy:demolition_sequence'],
                rationale='拆除工程应明确拆除顺序、解体清运流程及关键步序控制。',
            )
        )

        retained_pack_id, retained_pack_readiness = pack_by_rule.get('demolition_retained_structure_control_completeness', ('demolition.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='demolition_retained_structure_control_completeness',
                packId=retained_pack_id,
                packReadiness=retained_pack_readiness,
                matchType='direct_hit',
                status='hit' if not facts.projectFacts.get('demolitionRetainedStructureControlPresent') else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='high',
                factRefs=['project.demolitionRetainedStructureControlPresent'],
                evidenceRefs=['policy:demolition_retained_structure'],
                rationale='拆除工程应明确保留结构、作业平台承载或稳定状态控制要求。',
            )
        )

        calc_pack_id, calc_pack_readiness = pack_by_rule.get('demolition_support_calculation_traceability', ('demolition.base', 'ready'))
        calc_missing = not (facts.projectFacts.get('demolitionSupportCalculationPresent') or section_presence.get('calculationBook'))
        hits.append(
            RuleHit(
                ruleId='demolition_support_calculation_traceability',
                packId=calc_pack_id,
                packReadiness=calc_pack_readiness,
                matchType='direct_hit',
                status='hit' if calc_missing else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='high',
                factRefs=['project.demolitionSupportCalculationPresent', 'project.sectionPresence.calculationBook'],
                evidenceRefs=['policy:demolition_calculation'],
                rationale='拆除工程应形成临时支撑、吊运或爆破等计算依据。',
            )
        )
        return hits

    def _underground_excavation_hits(
        self,
        facts: ExtractedFacts,
        pack_by_rule: dict[str, tuple[str, str]],
        selected_pack_ids: set[str],
    ) -> list[RuleHit]:
        if 'underground_excavation.base' not in selected_pack_ids:
            return []
        hits: list[RuleHit] = []
        section_presence = facts.projectFacts.get('sectionPresence') or {}

        water_pack_id, water_pack_readiness = pack_by_rule.get('underground_excavation_water_control_completeness', ('underground_excavation.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='underground_excavation_water_control_completeness',
                packId=water_pack_id,
                packReadiness=water_pack_readiness,
                matchType='direct_hit',
                status='hit' if not facts.projectFacts.get('undergroundWaterControlPresent') else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='high',
                factRefs=['project.undergroundWaterControlPresent'],
                evidenceRefs=['policy:underground_excavation_water_control'],
                rationale='暗挖工程应明确地下水控制、注浆或冻结等关键水控制措施。',
            )
        )

        support_pack_id, support_pack_readiness = pack_by_rule.get('underground_excavation_support_parameters_completeness', ('underground_excavation.base', 'ready'))
        support_missing = not (
            facts.projectFacts.get('undergroundSupportParametersPresent') and section_presence.get('technicalParameters')
        )
        hits.append(
            RuleHit(
                ruleId='underground_excavation_support_parameters_completeness',
                packId=support_pack_id,
                packReadiness=support_pack_readiness,
                matchType='direct_hit',
                status='hit' if support_missing else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='high',
                factRefs=['project.undergroundSupportParametersPresent', 'project.sectionPresence.technicalParameters'],
                evidenceRefs=['policy:underground_excavation_support_parameters'],
                rationale='暗挖工程应明确开挖进尺、断面尺寸、支护参数和关键工装参数。',
            )
        )

        monitor_pack_id, monitor_pack_readiness = pack_by_rule.get('underground_excavation_monitoring_and_drawings', ('underground_excavation.base', 'ready'))
        monitor_gap = not (facts.projectFacts.get('undergroundMonitoringPresent') and section_presence.get('drawingSet'))
        hits.append(
            RuleHit(
                ruleId='underground_excavation_monitoring_and_drawings',
                packId=monitor_pack_id,
                packReadiness=monitor_pack_readiness,
                matchType='visibility_gap',
                status='manual_review_needed' if monitor_gap else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='medium',
                factRefs=['project.undergroundMonitoringPresent', 'project.sectionPresence.drawingSet', 'attachments.visibility'],
                evidenceRefs=['policy:underground_excavation_monitoring', 'policy:review_visibility_gap'],
                rationale='暗挖工程监测点布置图和周边环境平剖面图首轮按可视域优先处理。',
            )
        )
        return hits

    def _curtain_wall_installation_hits(
        self,
        facts: ExtractedFacts,
        pack_by_rule: dict[str, tuple[str, str]],
        selected_pack_ids: set[str],
    ) -> list[RuleHit]:
        if 'curtain_wall_installation.base' not in selected_pack_ids:
            return []
        hits: list[RuleHit] = []
        section_presence = facts.projectFacts.get('sectionPresence') or {}

        facility_pack_id, facility_pack_readiness = pack_by_rule.get('curtain_wall_installation_facility_integrity', ('curtain_wall_installation.base', 'ready'))
        facility_missing = not (
            facts.projectFacts.get('curtainWallFacilityPresent') and facts.projectFacts.get('curtainWallProtectionMeasuresPresent')
        )
        hits.append(
            RuleHit(
                ruleId='curtain_wall_installation_facility_integrity',
                packId=facility_pack_id,
                packReadiness=facility_pack_readiness,
                matchType='direct_hit',
                status='hit' if facility_missing else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='high',
                factRefs=['project.curtainWallFacilityPresent', 'project.curtainWallProtectionMeasuresPresent'],
                evidenceRefs=['policy:curtain_wall_installation_facility'],
                rationale='建筑幕墙安装工程应明确安装操作设施、附着支座和安全防护装置。',
            )
        )

        route_pack_id, route_pack_readiness = pack_by_rule.get('curtain_wall_installation_route_and_layout_completeness', ('curtain_wall_installation.base', 'ready'))
        route_missing = not (facts.projectFacts.get('curtainWallTransportRoutePresent') and section_presence.get('siteLayout'))
        hits.append(
            RuleHit(
                ruleId='curtain_wall_installation_route_and_layout_completeness',
                packId=route_pack_id,
                packReadiness=route_pack_readiness,
                matchType='direct_hit',
                status='hit' if route_missing else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='medium',
                factRefs=['project.curtainWallTransportRoutePresent', 'project.sectionPresence.siteLayout'],
                evidenceRefs=['policy:curtain_wall_installation_route_layout'],
                rationale='建筑幕墙安装工程应明确运输路线、吊装运行路线和堆放平面布置。',
            )
        )

        drawing_pack_id, drawing_pack_readiness = pack_by_rule.get('curtain_wall_installation_drawing_and_acceptance', ('curtain_wall_installation.base', 'ready'))
        drawing_gap = not (section_presence.get('drawingSet') and section_presence.get('acceptanceRequirements'))
        hits.append(
            RuleHit(
                ruleId='curtain_wall_installation_drawing_and_acceptance',
                packId=drawing_pack_id,
                packReadiness=drawing_pack_readiness,
                matchType='visibility_gap',
                status='manual_review_needed' if drawing_gap else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='medium',
                factRefs=['project.sectionPresence.drawingSet', 'project.sectionPresence.acceptanceRequirements', 'attachments.visibility'],
                evidenceRefs=['policy:curtain_wall_installation_drawings', 'policy:review_visibility_gap'],
                rationale='建筑幕墙安装工程相关图纸和验收章节首轮按可视域优先语义处理。',
            )
        )
        return hits

    def _manual_bored_pile_hits(
        self,
        facts: ExtractedFacts,
        pack_by_rule: dict[str, tuple[str, str]],
        selected_pack_ids: set[str],
    ) -> list[RuleHit]:
        if 'manual_bored_pile.base' not in selected_pack_ids:
            return []
        hits: list[RuleHit] = []

        jump_pack_id, jump_pack_readiness = pack_by_rule.get('manual_bored_pile_jump_excavation_integrity', ('manual_bored_pile.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='manual_bored_pile_jump_excavation_integrity',
                packId=jump_pack_id,
                packReadiness=jump_pack_readiness,
                matchType='direct_hit',
                status='hit' if not facts.projectFacts.get('manualBoredPileJumpExcavationPresent') else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='high',
                factRefs=['project.manualBoredPileJumpExcavationPresent'],
                evidenceRefs=['policy:manual_bored_pile_jump_excavation'],
                rationale='人工挖孔桩工程应明确跳挖、分区分序等作业组织要求。',
            )
        )

        gas_pack_id, gas_pack_readiness = pack_by_rule.get('manual_bored_pile_gas_and_electric_safety_completeness', ('manual_bored_pile.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='manual_bored_pile_gas_and_electric_safety_completeness',
                packId=gas_pack_id,
                packReadiness=gas_pack_readiness,
                matchType='direct_hit',
                status='hit' if not facts.projectFacts.get('manualBoredPileGasProtectionPresent') else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='high',
                factRefs=['project.manualBoredPileGasProtectionPresent'],
                evidenceRefs=['policy:manual_bored_pile_gas_electric_safety'],
                rationale='人工挖孔桩工程应明确有害气体检测、防中毒窒息和防触电措施。',
            )
        )

        forbidden_pack_id, forbidden_pack_readiness = pack_by_rule.get('manual_bored_pile_forbidden_conditions_manual_review', ('manual_bored_pile.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='manual_bored_pile_forbidden_conditions_manual_review',
                packId=forbidden_pack_id,
                packReadiness=forbidden_pack_readiness,
                matchType='visibility_gap',
                status='manual_review_needed' if facts.projectFacts.get('manualBoredPileForbiddenConditionMentioned') else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='high',
                factRefs=['project.manualBoredPileForbiddenConditionMentioned'],
                evidenceRefs=['policy:manual_bored_pile_forbidden_conditions'],
                rationale='人工挖孔桩禁用条件首轮仅做提示并进入人工复核，不直接自动下硬结论。',
            )
        )
        return hits

    def _steel_structure_installation_hits(
        self,
        facts: ExtractedFacts,
        pack_by_rule: dict[str, tuple[str, str]],
        selected_pack_ids: set[str],
    ) -> list[RuleHit]:
        if 'steel_structure_installation.base' not in selected_pack_ids:
            return []
        hits: list[RuleHit] = []
        section_presence = facts.projectFacts.get('sectionPresence') or {}

        lifting_pack_id, lifting_pack_readiness = pack_by_rule.get('steel_structure_installation_lifting_scheme_integrity', ('steel_structure_installation.base', 'ready'))
        lifting_missing = not (section_presence.get('technicalParameters') and section_presence.get('processFlow') and section_presence.get('processMethod'))
        hits.append(
            RuleHit(
                ruleId='steel_structure_installation_lifting_scheme_integrity',
                packId=lifting_pack_id,
                packReadiness=lifting_pack_readiness,
                matchType='direct_hit',
                status='hit' if lifting_missing else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='high',
                factRefs=['project.sectionPresence.technicalParameters', 'project.sectionPresence.processFlow', 'project.sectionPresence.processMethod'],
                evidenceRefs=['policy:steel_structure_installation_scheme'],
                rationale='钢结构安装工程应明确构件参数、吊装设备选型和安装流程。',
            )
        )

        support_pack_id, support_pack_readiness = pack_by_rule.get('steel_structure_installation_support_and_unloading', ('steel_structure_installation.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='steel_structure_installation_support_and_unloading',
                packId=support_pack_id,
                packReadiness=support_pack_readiness,
                matchType='direct_hit',
                status='hit' if not facts.projectFacts.get('steelSupportUnloadingPresent') else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='high',
                factRefs=['project.steelSupportUnloadingPresent'],
                evidenceRefs=['policy:steel_structure_installation_support'],
                rationale='钢结构安装工程应明确胎架、临时支撑、卸载条件等关键支撑链路。',
            )
        )

        drawing_pack_id, drawing_pack_readiness = pack_by_rule.get('steel_structure_installation_drawing_and_acceptance', ('steel_structure_installation.base', 'ready'))
        drawing_acceptance_gap = not section_presence.get('drawingSet') or not section_presence.get('acceptanceRequirements')
        hits.append(
            RuleHit(
                ruleId='steel_structure_installation_drawing_and_acceptance',
                packId=drawing_pack_id,
                packReadiness=drawing_pack_readiness,
                matchType='visibility_gap',
                status='manual_review_needed' if drawing_acceptance_gap else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='medium',
                factRefs=['project.sectionPresence.drawingSet', 'project.sectionPresence.acceptanceRequirements', 'attachments.visibility'],
                evidenceRefs=['policy:steel_structure_installation_drawings'],
                rationale='钢结构安装工程的措施图纸与验收章节首轮按可视域优先语义处理。',
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
        has_power_pack = bool({'temporary_power.base', 'power_outage_work.base'} & selected_pack_ids)
        has_supported_base = bool(
            {'construction_org.base', 'construction_scheme.base', 'distribution_network_special_scheme.base'}
            & selected_pack_ids
        )
        if not has_power_pack or not has_supported_base:
            return []
        if not facts.hazardFacts.get('temporaryPower'):
            return []
        targeted_titles = facts.emergencyFacts.get('planTitles') or []
        has_power_title = self._contains_keywords(targeted_titles, ('触电', '停送电', '临电', '用电'))
        measures_ready = bool(facts.hazardFacts.get('measureSectionPresent'))
        monitoring_ready = bool(facts.hazardFacts.get('monitoringSectionPresent'))
        status = 'pass' if measures_ready and monitoring_ready and has_power_title else 'hit'
        default_pack_id = 'power_outage_work.base' if 'power_outage_work.base' in selected_pack_ids else 'temporary_power.base'
        pack_id, pack_readiness = pack_by_rule.get('temporary_power_control_linkage', (default_pack_id, 'ready'))
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
