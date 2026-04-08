from __future__ import annotations

from src.review.schema import PolicyPack


def get_formwork_support_pack() -> PolicyPack:
    return PolicyPack(
        id='formwork_support.base',
        version='1.0.0',
        docTypes=['hazardous_special_scheme'],
        label='模板支撑体系',
        role='third_level',
        familyKey='hazardous_special_scheme',
        tier='3',
        disciplineTags=['formwork_support'],
        extractorIds=['project_facts', 'hazard_facts'],
        ruleIds=[
            'formwork_support_structure_completeness',
            'formwork_support_process_parameters',
            'formwork_support_calculation_traceability',
            'formwork_support_acceptance_completeness',
        ],
        evidencePackIds=['formwork_support.base'],
        defaultEnabled=False,
        description='模板支撑体系 type pack，补充技术参数、计算痕迹与验收要求检查。',
        readiness='ready',
        promotionCriteria={
            'ruleCoverage': True,
            'policyEvidenceReady': True,
            'testsReady': True,
            'versionedCasesReady': True,
        },
    )
