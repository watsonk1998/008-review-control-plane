from __future__ import annotations

from src.review.schema import PolicyPack


def get_demolition_pack() -> PolicyPack:
    return PolicyPack(
        id='demolition.base',
        version='1.0.0',
        docTypes=['hazardous_special_scheme'],
        label='拆除工程',
        role='third_level',
        familyKey='hazardous_special_scheme',
        tier='3',
        disciplineTags=['demolition'],
        extractorIds=['project_facts', 'hazard_facts'],
        ruleIds=[
            'demolition_sequence_integrity',
            'demolition_retained_structure_control_completeness',
            'demolition_support_calculation_traceability',
        ],
        evidencePackIds=['demolition.base'],
        defaultEnabled=False,
        description='拆除工程 type pack，补充拆除顺序、保留结构控制和临时支撑/吊运计算检查。',
        readiness='ready',
        promotionCriteria={
            'ruleCoverage': True,
            'policyEvidenceReady': True,
            'testsReady': True,
            'versionedCasesReady': True,
        },
    )
