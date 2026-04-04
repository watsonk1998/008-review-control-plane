from __future__ import annotations

from src.review.schema import PolicyPack


def get_lifting_operations_pack() -> PolicyPack:
    return PolicyPack(
        id='lifting_operations.base',
        version='1.0.0',
        docTypes=['construction_org', 'hazardous_special_scheme', 'construction_scheme'],
        disciplineTags=['lifting_operations'],
        extractorIds=['hazard_facts', 'schedule_resource_facts'],
        ruleIds=[
            'lifting_operations_special_scheme_linkage',
            'lifting_operations_calculation_traceability',
        ],
        evidencePackIds=['hazardous_special_scheme.base', 'review.emergency'],
        defaultEnabled=False,
        description='起重吊装场景 pack，补充专项方案挂接与吊装参数/验算可追溯性检查。',
        readiness='ready',
        promotionCriteria={
            'ruleCoverage': True,
            'policyEvidenceReady': True,
            'testsReady': True,
            'versionedCasesReady': True,
        },
    )
