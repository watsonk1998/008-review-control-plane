from __future__ import annotations

"""Canonical review-module bindings for Hermes main review + support + decision flow.

This table is the single source of truth for:
- frontend-facing module names
- Hermes main-review templates
- 008 support capabilities
- Hermes decision policy hints
- final result buckets
"""

from typing import Literal

from pydantic import BaseModel, Field


class ReviewModuleBinding(BaseModel):
    module_name: str
    title: str
    hermes_templates: list[str] = Field(default_factory=list)
    support_capabilities: list[str] = Field(default_factory=list)
    decision_policy: str
    result_bucket: str


REVIEW_MODULE_BINDINGS: dict[str, ReviewModuleBinding] = {
    'structure_completeness': ReviewModuleBinding(
        module_name='structure_completeness',
        title='结构完整性',
        hermes_templates=['structure_completeness_reviewer'],
        support_capabilities=['primary_support_review', 'profile_and_packs'],
        decision_policy='prefer_conservative_structure_gap_expression',
        result_bucket='structure_completeness',
    ),
    'parameter_consistency': ReviewModuleBinding(
        module_name='parameter_consistency',
        title='参数一致性',
        hermes_templates=['execution_risk_reviewer', 'power_outage_operation_chain_reviewer'],
        support_capabilities=['fact_extract', 'rule_and_evidence'],
        decision_policy='require_support_for_parameter_conflict',
        result_bucket='parameter_consistency',
    ),
    'legality_compliance': ReviewModuleBinding(
        module_name='legality_compliance',
        title='合法合规性',
        hermes_templates=['policy_compliance_reviewer', 'power_outage_normative_reviewer', 'power_outage_restoration_closure_reviewer'],
        support_capabilities=['profile_and_packs', 'rule_and_evidence'],
        decision_policy='promote_when_rule_hits_are_grounded',
        result_bucket='legality_compliance',
    ),
    'execution_continuity': ReviewModuleBinding(
        module_name='execution_continuity',
        title='工序连贯性',
        hermes_templates=['execution_risk_reviewer', 'power_outage_operation_chain_reviewer'],
        support_capabilities=['fact_extract', 'rule_and_evidence'],
        decision_policy='prefer_conservative_sequence_expression',
        result_bucket='execution_continuity',
    ),
    'evidence_validation': ReviewModuleBinding(
        module_name='evidence_validation',
        title='证据验证',
        hermes_templates=['visibility_gap_reviewer', 'normative_validity_reviewer'],
        support_capabilities=['parse_visibility', 'rule_and_evidence'],
        decision_policy='degrade_when_evidence_is_insufficient',
        result_bucket='evidence_validation',
    ),
}

TEMPLATE_TO_REVIEW_MODULES: dict[str, list[str]] = {}
for binding in REVIEW_MODULE_BINDINGS.values():
    for template_id in binding.hermes_templates:
        TEMPLATE_TO_REVIEW_MODULES.setdefault(template_id, []).append(binding.module_name)


def module_binding(module_name: str) -> ReviewModuleBinding:
    return REVIEW_MODULE_BINDINGS[module_name]


def module_titles() -> dict[str, str]:
    return {name: binding.title for name, binding in REVIEW_MODULE_BINDINGS.items()}


def module_template_ids(module_names: list[str]) -> list[str]:
    out: list[str] = []
    for module_name in module_names:
        binding = REVIEW_MODULE_BINDINGS.get(module_name)
        if not binding:
            continue
        for template_id in binding.hermes_templates:
            if template_id not in out:
                out.append(template_id)
    return out


def template_review_modules(template_id: str) -> list[str]:
    return list(TEMPLATE_TO_REVIEW_MODULES.get(template_id, []))
