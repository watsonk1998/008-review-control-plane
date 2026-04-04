from __future__ import annotations

from src.review.schema import PolicyPack


def get_supervision_plan_base_pack() -> PolicyPack:
    return PolicyPack(
        id='supervision_plan.base',
        version='1.0.0',
        docTypes=['supervision_plan'],
        extractorIds=['project_facts', 'hazard_facts', 'schedule_resource_facts'],
        ruleIds=[
            'supervision_plan_structure_completeness',
            'supervision_plan_monitoring_linkage',
            'supervision_plan_attachment_visibility',
        ],
        evidencePackIds=['supervision_plan.base', 'review.visibility'],
        defaultEnabled=True,
        description='监理规划基础 pack，覆盖核心章节、监测监控与附件可视域。',
        readiness='ready',
        promotionCriteria={
            'ruleCoverage': True,
            'policyEvidenceReady': True,
            'testsReady': True,
            'versionedCasesReady': True,
        },
    )
