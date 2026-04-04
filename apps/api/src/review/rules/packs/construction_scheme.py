from __future__ import annotations

from src.review.schema import PolicyPack


def get_construction_scheme_base_pack() -> PolicyPack:
    return PolicyPack(
        id='construction_scheme.base',
        version='1.0.0',
        docTypes=['construction_scheme'],
        disciplineTags=['lifting_operations', 'temporary_power', 'hot_work'],
        extractorIds=['project_facts', 'hazard_facts', 'schedule_resource_facts'],
        ruleIds=[
            'construction_scheme_structure_completeness',
            'construction_scheme_attachment_visibility',
        ],
        evidencePackIds=['construction_scheme.base', 'review.visibility'],
        defaultEnabled=True,
        description='一般施工方案基础 pack，覆盖最小结构完整性与附件可视域收口。',
        readiness='ready',
        promotionCriteria={
            'ruleCoverage': True,
            'policyEvidenceReady': True,
            'testsReady': True,
            'versionedCasesReady': True,
        },
    )
