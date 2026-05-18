from __future__ import annotations

import json
from pathlib import Path

from src.domain.models import ReviewLayer
from src.review.schema import ExtractedFacts, PolicyPack, RuleHit

_CONSTRUCTION_ORG_RULES_PATH = (
    Path(__file__).resolve().parents[5] / "config" / "review_rules" / "construction_org_rules.json"
)


def _load_construction_org_rules() -> list[dict]:
    if not _CONSTRUCTION_ORG_RULES_PATH.exists():
        return []
    with open(_CONSTRUCTION_ORG_RULES_PATH, encoding="utf-8") as f:
        return json.load(f)


class ReviewRuleEngine:
    def run(self, facts: ExtractedFacts, packs: list[PolicyPack], parse_result) -> list[RuleHit]:
        pack_by_rule: dict[str, tuple[str, str]] = {}
        selected_pack_ids = {pack.id for pack in packs}
        for pack in packs:
            for rule_id in pack.ruleIds:
                pack_by_rule.setdefault(rule_id, (pack.id, pack.readiness))

        hits: list[RuleHit] = []
        hits.extend(self._construction_org_hits(facts, pack_by_rule))
        hits.extend(self._construction_org_clause_hits(facts, pack_by_rule, parse_result))
        hits.extend(self._construction_scheme_hits(facts, pack_by_rule))
        hits.extend(self._hazardous_special_scheme_hits(facts, pack_by_rule))
        hits.extend(self._distribution_network_special_scheme_hits(facts, pack_by_rule, parse_result))
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
        hits.extend(self._power_outage_work_hits(facts, pack_by_rule, selected_pack_ids, parse_result))
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

    def _construction_org_clause_hits(
        self, facts: ExtractedFacts, pack_by_rule: dict[str, tuple[str, str]], parse_result
    ) -> list[RuleHit]:
        """Evaluate clause-level rules from JSON rule set against parsed document."""
        if not any(
            pid == "construction_org.base" for pid, _ in pack_by_rule.values()
        ):
            return []

        rules = _load_construction_org_rules()
        if not rules:
            return []

        # Build fact lookup from structure completeness and section presence
        structure_rows = facts.projectFacts.get("structureCompleteness") or []
        structure_map = {row["itemKey"]: row for row in structure_rows}
        section_presence = facts.projectFacts.get("sectionPresence") or {}

        # Build text content index from parse_result for keyword matching
        block_texts: list[str] = []
        if parse_result is not None:
            for block in getattr(parse_result, "blocks", []) or []:
                text = str(block.get("text") or "").strip()
                if text:
                    block_texts.append(text)
        full_text = "\n".join(block_texts)

        hits: list[RuleHit] = []
        for rule in rules:
            if not rule.get("enabled", True):
                continue

            rule_id = rule["rule_id"]
            item_code = rule["review_item_code"]
            rule_desc = rule["rule_description"]

            # Determine pack and readiness
            pack_key = f"construction_org_clause_{rule_id}"
            pack_id, pack_readiness = pack_by_rule.get(
                pack_key, ("construction_org.base", "ready")
            )

            # Evaluate rule based on review_item_code category
            status, severity, fact_refs, evidence_refs = self._evaluate_clause_rule(
                rule, structure_map, section_presence, full_text
            )

            hits.append(
                RuleHit(
                    ruleId=pack_key,
                    packId=pack_id,
                    packReadiness=pack_readiness,
                    matchType="direct_hit",
                    status=status,
                    layerHint=ReviewLayer.L1 if item_code == "structure_integrity" else ReviewLayer.L2,
                    severityHint=severity,
                    factRefs=fact_refs,
                    evidenceRefs=evidence_refs,
                    rationale=rule_desc[:200],
                )
            )

        return hits

    def _evaluate_clause_rule(
        self,
        rule: dict,
        structure_map: dict,
        section_presence: dict,
        full_text: str,
    ) -> tuple[str, str, list[str], list[str]]:
        """Evaluate a single clause rule. Returns (status, severity, factRefs, evidenceRefs)."""
        item_code = rule["review_item_code"]
        rule_desc = rule["rule_description"]

        # Map review_item_code to structure item keys
        _ITEM_TO_STRUCTURE_KEY = {
            "structure_integrity": "preparationBasis",
            "basis_accuracy": "preparationBasis",
            "consistency_check": "constructionDeployment",
            "content_compliance": "engineeringOverview",
            "calculation_review": "processMethod",
        }

        structure_key = _ITEM_TO_STRUCTURE_KEY.get(item_code, "engineeringOverview")
        structure_row = structure_map.get(structure_key)

        # For structure_integrity rules: check if the relevant section exists
        if item_code == "structure_integrity":
            if structure_row and structure_row.get("status") == "missing":
                return "hit", "high", [f"project.structureCompleteness.{structure_key}"], ["policy:construction_org_structure"]
            elif structure_row and structure_row.get("status") == "partial":
                return "hit", "medium", [f"project.structureCompleteness.{structure_key}"], ["policy:construction_org_structure"]
            return "pass", "low", [f"project.structureCompleteness.{structure_key}"], ["policy:construction_org_structure"]

        # For content_compliance and other rules: keyword-based check
        keywords = self._extract_keywords_from_rule(rule_desc)
        if keywords and not any(kw in full_text for kw in keywords):
            return "manual_review_needed", "medium", [f"project.sectionPresence.{structure_key}"], ["policy:construction_org_clause_rules"]

        return "pass", "low", [f"project.sectionPresence.{structure_key}"], ["policy:construction_org_clause_rules"]

    @staticmethod
    def _extract_keywords_from_rule(rule_desc: str) -> list[str]:
        """Extract checkable keywords from rule description for document matching."""
        import re
        keywords = []
        match = re.search(r'应(?:包括|包含|设置|建立|明确|识别|制定)(.*?)(?:（|$)', rule_desc)
        if match:
            items = re.split(r'[、；;]', match.group(1))
            for item in items:
                item = item.strip().strip('等')
                if len(item) >= 2:
                    keywords.append(item)
        return keywords[:5]

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
        structure_rows = facts.projectFacts.get('structureCompleteness') or []
        common_rows = [row for row in structure_rows if row.get('scope') == 'common']
        deficient_rows = [row for row in common_rows if row.get('status') in {'missing', 'partial'}]
        blocked_rows = [row for row in common_rows if row.get('status') == 'blocked_by_visibility']
        fact_refs = [f'project.structureCompleteness.{row["itemKey"]}' for row in [*deficient_rows, *blocked_rows]]
        if not common_rows:
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
            fact_refs = [f'project.sectionPresence.{key}' for key in missing_core_sections] or ['project.sectionPresence.engineeringOverview']
            has_core_gap = bool(missing_core_sections)
            severity = 'high'
        else:
            has_core_gap = bool(deficient_rows or blocked_rows)
            severity = 'high' if any(row.get('status') == 'missing' for row in deficient_rows) else 'medium'
        core_pack_id, core_pack_readiness = pack_by_rule.get('hazardous_special_scheme_core_sections', ('hazardous_special_scheme.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='hazardous_special_scheme_core_sections',
                packId=core_pack_id,
                packReadiness=core_pack_readiness,
                matchType='direct_hit',
                status='hit' if has_core_gap else 'pass',
                layerHint=ReviewLayer.L1,
                severityHint=severity,
                factRefs=fact_refs,
                evidenceRefs=['policy:hazardous_scheme_structure'],
                rationale='危大专项方案在具体三级专项之外，仍应满足专项施工方案通用目录要求。',
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

    def _distribution_network_special_scheme_hits(
        self,
        facts: ExtractedFacts,
        pack_by_rule: dict[str, tuple[str, str]],
        parse_result,
    ) -> list[RuleHit]:
        if not any(pack_id == 'distribution_network_special_scheme.base' for pack_id, _ in pack_by_rule.values()):
            return []
        hits: list[RuleHit] = []
        section_presence = facts.projectFacts.get('sectionPresence') or {}
        structure_rows = facts.projectFacts.get('structureCompleteness') or []
        common_rows = [row for row in structure_rows if row.get('scope') == 'common']
        deficient_rows = [row for row in common_rows if row.get('status') in {'missing', 'partial'}]
        blocked_rows = [row for row in common_rows if row.get('status') == 'blocked_by_visibility']
        fact_refs = [f'project.structureCompleteness.{row["itemKey"]}' for row in [*deficient_rows, *blocked_rows]]
        if not common_rows:
            fact_refs = ['project.structureCompleteness.specialEngineeringOverview']
        pack_id, pack_readiness = pack_by_rule.get(
            'distribution_network_special_scheme_structure_completeness',
            ('distribution_network_special_scheme.base', 'ready'),
        )
        hits.append(
            RuleHit(
                ruleId='distribution_network_special_scheme_structure_completeness',
                packId=pack_id,
                packReadiness=pack_readiness,
                matchType='direct_hit',
                status='hit' if deficient_rows or blocked_rows else 'pass',
                layerHint=ReviewLayer.L1,
                severityHint='high' if any(row.get('status') == 'missing' for row in deficient_rows) else 'medium',
                factRefs=fact_refs,
                evidenceRefs=['policy:distribution_network_special_scheme_structure'],
                rationale='配网工程专项施工方案在具体三级专项之外，仍应满足专项施工方案通用目录要求。',
            )
        )

        risk_pack_id, risk_pack_readiness = pack_by_rule.get(
            'distribution_network_special_scheme_risk_identification',
            ('distribution_network_special_scheme.base', 'ready'),
        )
        hits.append(
            RuleHit(
                ruleId='distribution_network_special_scheme_risk_identification',
                packId=risk_pack_id,
                packReadiness=risk_pack_readiness,
                matchType='direct_hit',
                status='pass' if section_presence.get('riskIdentification') else 'hit',
                layerHint=ReviewLayer.L2,
                severityHint='medium',
                factRefs=['project.sectionPresence.riskIdentification'],
                evidenceRefs=['policy:distribution_network_special_scheme_risk_identification'],
                rationale='配网专项方案应明确风险辨识、分级与作业边界内的主要危险源。',
            )
        )

        drawing_present = bool(section_presence.get('drawingSet'))
        boundary_present = bool(section_presence.get('siteLayout') or section_presence.get('surroundingConditions'))
        drawing_pack_id, drawing_pack_readiness = pack_by_rule.get(
            'distribution_network_special_scheme_drawings_and_boundary',
            ('distribution_network_special_scheme.base', 'ready'),
        )
        hits.append(
            RuleHit(
                ruleId='distribution_network_special_scheme_drawings_and_boundary',
                packId=drawing_pack_id,
                packReadiness=drawing_pack_readiness,
                matchType='visibility_gap' if not drawing_present else 'direct_hit',
                status='manual_review_needed' if not drawing_present else ('hit' if not boundary_present else 'pass'),
                layerHint=ReviewLayer.L2,
                severityHint='medium',
                factRefs=['project.sectionPresence.drawingSet', 'project.sectionPresence.siteLayout', 'project.sectionPresence.surroundingConditions', 'attachments.visibility'],
                evidenceRefs=['policy:distribution_network_special_scheme_drawings'],
                rationale='配网专项方案应具备图纸、平面布置或周边环境条件，以界定施工边界和影响对象。',
            )
        )

        targeted_titles = facts.emergencyFacts.get('planTitles') or []
        has_targeted_title = self._contains_keywords(targeted_titles, ('触电', '停电', '停送电', '配网', '送电'))
        emergency_pack_id, emergency_pack_readiness = pack_by_rule.get(
            'distribution_network_special_scheme_emergency_targeted',
            ('distribution_network_special_scheme.base', 'ready'),
        )
        hits.append(
            RuleHit(
                ruleId='distribution_network_special_scheme_emergency_targeted',
                packId=emergency_pack_id,
                packReadiness=emergency_pack_readiness,
                matchType='direct_hit',
                status='pass' if has_targeted_title else 'hit',
                layerHint=ReviewLayer.L2,
                severityHint='medium',
                factRefs=['emergency.planTitles', 'hazard.temporaryPower'],
                evidenceRefs=['policy:distribution_network_special_scheme_emergency', 'policy:emergency_plan_targeted'],
                rationale='配网停电专项应围绕触电、误送电等主要风险建立针对性应急安排。',
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
        structure_rows = facts.projectFacts.get('structureCompleteness') or []
        special_rows = [row for row in structure_rows if row.get('scope') == 'special']
        deficient_rows = [row for row in special_rows if row.get('status') in {'missing', 'partial'}]
        blocked_rows = [row for row in special_rows if row.get('status') == 'blocked_by_visibility']
        fact_refs = [f'project.structureCompleteness.{row["itemKey"]}' for row in [*deficient_rows, *blocked_rows]]
        if not special_rows:
            fact_refs = ['project.structureCompleteness.foundationPitSupportSequence']
        structure_pack_id, structure_pack_readiness = pack_by_rule.get('foundation_pit_structure_completeness', ('foundation_pit.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='foundation_pit_structure_completeness',
                packId=structure_pack_id,
                packReadiness=structure_pack_readiness,
                matchType='direct_hit',
                status='hit' if deficient_rows or blocked_rows else 'pass',
                layerHint=ReviewLayer.L1,
                severityHint='high' if any(row.get('status') == 'missing' for row in deficient_rows) else 'medium',
                factRefs=fact_refs,
                evidenceRefs=['policy:foundation_pit_structure'],
                rationale='基坑工程专项方案除通用要求外，还应覆盖支护/降水/开挖及加撑关系、监测监控、周边环境与监测点相关图纸及验收要求。',
            )
        )

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
        structure_rows = facts.projectFacts.get('structureCompleteness') or []
        special_rows = [row for row in structure_rows if row.get('scope') == 'special']
        deficient_rows = [row for row in special_rows if row.get('status') in {'missing', 'partial'}]
        blocked_rows = [row for row in special_rows if row.get('status') == 'blocked_by_visibility']
        fact_refs = [f'project.structureCompleteness.{row["itemKey"]}' for row in [*deficient_rows, *blocked_rows]]
        if not special_rows:
            fact_refs = ['project.structureCompleteness.formworkSupportParameters']
        structure_pack_id, structure_pack_readiness = pack_by_rule.get('formwork_support_structure_completeness', ('formwork_support.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='formwork_support_structure_completeness',
                packId=structure_pack_id,
                packReadiness=structure_pack_readiness,
                matchType='direct_hit',
                status='hit' if deficient_rows or blocked_rows else 'pass',
                layerHint=ReviewLayer.L1,
                severityHint='high' if any(row.get('status') == 'missing' for row in deficient_rows) else 'medium',
                factRefs=fact_refs,
                evidenceRefs=['policy:formwork_support_structure'],
                rationale='模板支撑体系专项方案除通用要求外，还应覆盖技术参数、工艺流程/浇筑顺序、计算依据和验收要求。',
            )
        )

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
        structure_rows = facts.projectFacts.get('structureCompleteness') or []
        special_rows = [row for row in structure_rows if row.get('scope') == 'special']
        deficient_rows = [row for row in special_rows if row.get('status') in {'missing', 'partial'}]
        blocked_rows = [row for row in special_rows if row.get('status') == 'blocked_by_visibility']
        fact_refs = [f'project.structureCompleteness.{row["itemKey"]}' for row in [*deficient_rows, *blocked_rows]]
        if not special_rows:
            fact_refs = ['project.structureCompleteness.steelStructureComponentParameters']
        structure_pack_id, structure_pack_readiness = pack_by_rule.get('steel_structure_installation_structure_completeness', ('steel_structure_installation.base', 'ready'))
        hits.append(
            RuleHit(
                ruleId='steel_structure_installation_structure_completeness',
                packId=structure_pack_id,
                packReadiness=structure_pack_readiness,
                matchType='direct_hit',
                status='hit' if deficient_rows or blocked_rows else 'pass',
                layerHint=ReviewLayer.L1,
                severityHint='high' if any(row.get('status') == 'missing' for row in deficient_rows) else 'medium',
                factRefs=fact_refs,
                evidenceRefs=['policy:steel_structure_installation_structure'],
                rationale='钢结构安装专项方案除通用要求外，还应覆盖构件参数、吊装设备选型、安装流程、支撑/卸载条件及措施图纸和验收章节。',
            )
        )

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

    def _power_outage_work_hits(
        self,
        facts: ExtractedFacts,
        pack_by_rule: dict[str, tuple[str, str]],
        selected_pack_ids: set[str],
        parse_result,
    ) -> list[RuleHit]:
        if 'power_outage_work.base' not in selected_pack_ids:
            return []
        hits: list[RuleHit] = []
        structure_rows = facts.projectFacts.get('structureCompleteness') or []
        section_presence = facts.projectFacts.get('sectionPresence') or {}
        special_rows = [row for row in structure_rows if row.get('scope') == 'special']
        deficient_rows = [row for row in special_rows if row.get('status') in {'missing', 'partial'}]
        blocked_rows = [row for row in special_rows if row.get('status') == 'blocked_by_visibility']
        fact_refs = [f'project.structureCompleteness.{row["itemKey"]}' for row in [*deficient_rows, *blocked_rows]]
        if not special_rows:
            fact_refs = ['project.structureCompleteness.powerOutageScope']
        normalized_text = self._normalized_text(parse_result)
        outage_scope_ready = self._text_contains_keywords(normalized_text, ('停电范围', '停电线路', '停电设备', '停电线路及设备范围'))
        work_content_ready = self._text_contains_keywords(normalized_text, ('作业内容', '工作内容', '施工内容', '作业任务'))
        outage_time_ready = self._text_contains_keywords(normalized_text, ('停电时间', '停电起止', '计划停电', '恢复送电时间', '送电时间', '恢复时间'))
        important_user_ready = self._text_contains_keywords(normalized_text, ('重要用户', '保供', '用户告知', '停电通知'))
        personnel_ready = self._text_contains_keywords(normalized_text, ('工作负责人', '监护人', '特种作业', '持证', '上岗证', '培训', '交底'))
        approval_ready = self._text_contains_keywords(normalized_text, ('停电申请', '审批', '批复', '许可', '工作许可', '用户告知', '调度许可'))
        survey_ready = self._text_contains_keywords(normalized_text, ('现场勘察', '勘察记录', '现场踏勘'))
        ticket_ready = self._text_contains_keywords(normalized_text, ('工作票', '操作票', '工作许可'))
        grounding_ready = self._text_contains_keywords(normalized_text, ('接地线', '接地装置', '验电', '挂接地线', '拆接地线'))
        acceptance_ready = bool(section_presence.get('acceptanceRequirements')) or self._text_contains_keywords(normalized_text, ('验收', '质量控制', '质量管控', '验收要求'))
        five_step_tokens = ('停电', '验电', '接地', '挂牌', '遮栏')
        five_step_count = sum(1 for token in five_step_tokens if token in normalized_text)
        anti_backfeed_count = sum(1 for token in ('反送电', '倒送电', '双电源', '低压反送电') if token in normalized_text)
        restoration_count = sum(
            1
            for token in ('完工检查', '拆接地线', '恢复送电', '送电恢复', '资料归档', '整改闭环', '终结手续')
            if token in normalized_text
        )

        pack_id, pack_readiness = pack_by_rule.get(
            'power_outage_work_structure_completeness',
            ('power_outage_work.base', 'ready'),
        )
        hits.append(
            RuleHit(
                ruleId='power_outage_work_structure_completeness',
                packId=pack_id,
                packReadiness=pack_readiness,
                matchType='direct_hit',
                status='hit' if deficient_rows or blocked_rows else 'pass',
                layerHint=ReviewLayer.L1,
                severityHint='high' if any(row.get('status') == 'missing' for row in deficient_rows) else 'medium',
                factRefs=fact_refs,
                evidenceRefs=['policy:power_outage_work_structure'],
                rationale='停电施工作业专项施工方案除通用要求外，还应覆盖停电范围、作业内容、主要风险、人员、机具、材料、安全/质量管控与应急措施。',
            )
        )

        basic_pack_id, basic_pack_readiness = pack_by_rule.get(
            'power_outage_work_basic_info_integrity',
            ('power_outage_work.base', 'ready'),
        )
        basic_missing_refs: list[str] = []
        if not outage_scope_ready:
            basic_missing_refs.append('project.structureCompleteness.powerOutageScope')
        if not work_content_ready:
            basic_missing_refs.append('project.structureCompleteness.powerOutageWorkContent')
        if not outage_time_ready:
            basic_missing_refs.append('schedule.shutdownWindowDays')
        if not important_user_ready:
            basic_missing_refs.append('project.sectionPresence.specialPreparationBasis')
        hits.append(
            RuleHit(
                ruleId='power_outage_work_basic_info_integrity',
                packId=basic_pack_id,
                packReadiness=basic_pack_readiness,
                matchType='inferred_risk',
                status='hit' if basic_missing_refs else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='high' if len(basic_missing_refs) >= 2 else 'medium',
                factRefs=basic_missing_refs or ['project.structureCompleteness.powerOutageScope'],
                evidenceRefs=['policy:power_outage_work_basic_info'],
                rationale='停电施工方案应明确停电范围、作业内容、停复电时间以及重要用户保障等基础信息。',
            )
        )

        personnel_pack_id, personnel_pack_readiness = pack_by_rule.get(
            'power_outage_work_personnel_qualification_and_training',
            ('power_outage_work.base', 'ready'),
        )
        personnel_refs = []
        if not any(self._matches_structure_item(row, 'powerOutageStaffing') for row in special_rows):
            personnel_refs.append('project.structureCompleteness.powerOutageStaffing')
        if not personnel_ready:
            personnel_refs.append('resource.laborTotal')
        hits.append(
            RuleHit(
                ruleId='power_outage_work_personnel_qualification_and_training',
                packId=personnel_pack_id,
                packReadiness=personnel_pack_readiness,
                matchType='inferred_risk',
                status='hit' if personnel_refs else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='medium',
                factRefs=personnel_refs or ['project.structureCompleteness.powerOutageStaffing'],
                evidenceRefs=['policy:power_outage_work_personnel_training'],
                rationale='停电施工方案应明确工作负责人、监护人、持证上岗、培训交底和现场监护安排。',
            )
        )

        approval_pack_id, approval_pack_readiness = pack_by_rule.get(
            'power_outage_work_application_approval_linkage',
            ('power_outage_work.base', 'ready'),
        )
        approval_refs = []
        if not approval_ready:
            approval_refs.extend(['project.sectionPresence.preparationBasis', 'project.sectionPresence.processMethod'])
        hits.append(
            RuleHit(
                ruleId='power_outage_work_application_approval_linkage',
                packId=approval_pack_id,
                packReadiness=approval_pack_readiness,
                matchType='inferred_risk',
                status='hit' if approval_refs else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='high',
                factRefs=approval_refs or ['project.sectionPresence.preparationBasis'],
                evidenceRefs=['policy:power_outage_work_application_approval'],
                rationale='停电施工作业应形成停电申请、审批、许可办理及用户告知等前置手续闭环。',
            )
        )

        five_step_pack_id, five_step_pack_readiness = pack_by_rule.get(
            'power_outage_work_shutdown_five_step_closure',
            ('power_outage_work.base', 'ready'),
        )
        five_step_refs = []
        if five_step_count < 4:
            five_step_refs.extend(['project.sectionPresence.processMethod', 'project.structureCompleteness.powerOutageSafetyControl'])
        hits.append(
            RuleHit(
                ruleId='power_outage_work_shutdown_five_step_closure',
                packId=five_step_pack_id,
                packReadiness=five_step_pack_readiness,
                matchType='inferred_risk',
                status='hit' if five_step_refs else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='high',
                factRefs=five_step_refs or ['project.sectionPresence.processMethod'],
                evidenceRefs=['policy:power_outage_work_five_step'],
                rationale='停电作业应围绕停电、验电、接地、挂牌、遮栏建立全过程安全措施闭环。',
            )
        )

        anti_pack_id, anti_pack_readiness = pack_by_rule.get(
            'power_outage_work_anti_backfeed_controls',
            ('power_outage_work.base', 'ready'),
        )
        anti_refs = []
        if anti_backfeed_count == 0:
            anti_refs.extend(['hazard.temporaryPower', 'project.structureCompleteness.powerOutageSafetyControl'])
        hits.append(
            RuleHit(
                ruleId='power_outage_work_anti_backfeed_controls',
                packId=anti_pack_id,
                packReadiness=anti_pack_readiness,
                matchType='inferred_risk',
                status='hit' if anti_refs else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='high',
                factRefs=anti_refs or ['hazard.temporaryPower'],
                evidenceRefs=['policy:power_outage_work_anti_backfeed'],
                rationale='停电施工方案应针对双电源、反送电、倒送电等场景设置防误送电控制措施。',
            )
        )

        ticket_survey_pack_id, ticket_survey_pack_readiness = pack_by_rule.get(
            'power_outage_work_work_ticket_and_site_survey',
            ('power_outage_work.base', 'ready'),
        )
        ticket_survey_refs = []
        if not ticket_ready:
            ticket_survey_refs.append('project.sectionPresence.processMethod')
        if not survey_ready:
            ticket_survey_refs.append('project.sectionPresence.specialPreparationBasis')
        hits.append(
            RuleHit(
                ruleId='power_outage_work_work_ticket_and_site_survey',
                packId=ticket_survey_pack_id,
                packReadiness=ticket_survey_pack_readiness,
                matchType='inferred_risk',
                status='hit' if ticket_survey_refs else 'pass',
                layerHint=ReviewLayer.L3,
                severityHint='medium',
                factRefs=ticket_survey_refs or ['project.sectionPresence.processMethod'],
                evidenceRefs=['policy:power_outage_work_application_approval'],
                rationale='停电作业应具备工作票、操作票和现场勘察记录等前置证据链。',
            )
        )

        controls_pack_id, controls_pack_readiness = pack_by_rule.get(
            'power_outage_work_safety_and_quality_controls',
            ('power_outage_work.base', 'ready'),
        )
        missing_control_refs = []
        if not any(self._matches_structure_item(row, 'powerOutageSafetyControl') for row in special_rows):
            missing_control_refs.append('project.structureCompleteness.powerOutageSafetyControl')
        if not any(self._matches_structure_item(row, 'powerOutageQualityControl') for row in special_rows):
            missing_control_refs.append('project.structureCompleteness.powerOutageQualityControl')
        if not acceptance_ready:
            missing_control_refs.append('project.sectionPresence.acceptanceRequirements')
        hits.append(
            RuleHit(
                ruleId='power_outage_work_safety_and_quality_controls',
                packId=controls_pack_id,
                packReadiness=controls_pack_readiness,
                matchType='direct_hit',
                status='hit' if missing_control_refs else 'pass',
                layerHint=ReviewLayer.L2,
                severityHint='medium',
                factRefs=missing_control_refs or ['project.structureCompleteness.powerOutageSafetyControl'],
                evidenceRefs=['policy:power_outage_work_controls'],
                rationale='停电施工作业专项应将安全控制、质量控制和关键验收点串成稳定的执行控制链。',
            )
        )

        ticket_pack_id, ticket_pack_readiness = pack_by_rule.get(
            'power_outage_work_ticket_grounding_traceability',
            ('power_outage_work.base', 'ready'),
        )
        hits.append(
            RuleHit(
                ruleId='power_outage_work_ticket_grounding_traceability',
                packId=ticket_pack_id,
                packReadiness=ticket_pack_readiness,
                matchType='inferred_risk',
                status='pass' if (grounding_ready and ticket_ready) else 'hit',
                layerHint=ReviewLayer.L3,
                severityHint='high',
                factRefs=['project.structureCompleteness.powerOutageScope', 'project.sectionPresence.processMethod'],
                evidenceRefs=['policy:power_outage_work_ticket_grounding'],
                rationale='停电施工作业应对工作票/操作票、验电和接地线等关键执行证据链形成可追溯表达。',
            )
        )

        restoration_pack_id, restoration_pack_readiness = pack_by_rule.get(
            'power_outage_work_restoration_and_archive_closure',
            ('power_outage_work.base', 'ready'),
        )
        restoration_refs = []
        if restoration_count < 3:
            restoration_refs.extend(['project.sectionPresence.acceptanceRequirements', 'project.structureCompleteness.powerOutageEmergencyMeasures'])
        hits.append(
            RuleHit(
                ruleId='power_outage_work_restoration_and_archive_closure',
                packId=restoration_pack_id,
                packReadiness=restoration_pack_readiness,
                matchType='inferred_risk',
                status='hit' if restoration_refs else 'pass',
                layerHint=ReviewLayer.L3,
                severityHint='medium',
                factRefs=restoration_refs or ['project.sectionPresence.acceptanceRequirements'],
                evidenceRefs=['policy:power_outage_work_restoration_closure'],
                rationale='停电施工作业应明确完工检查、拆接地线、恢复送电、资料归档及整改闭环要求。',
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
        if 'hot_work.base' not in selected_pack_ids or not ({'construction_org.base', 'construction_scheme.base', 'distribution_network_special_scheme.base'} & selected_pack_ids):
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

    def _normalized_text(self, parse_result) -> str:
        return str(getattr(parse_result, 'normalizedText', '') or '')

    def _text_contains_keywords(self, text: str, keywords: tuple[str, ...]) -> bool:
        return any(keyword in text for keyword in keywords)

    def _contains_keywords(self, values: list[str], keywords: tuple[str, ...]) -> bool:
        return any(any(keyword in str(value) for keyword in keywords) for value in values)

    def _matches_structure_item(self, row: dict, item_key: str) -> bool:
        return row.get('itemKey') == item_key and row.get('status') in {'matched', 'partial'}
