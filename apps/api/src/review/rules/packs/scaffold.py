from __future__ import annotations

from src.review.schema import PolicyPack


def get_scaffold_pack() -> PolicyPack:
    return PolicyPack(
        id='scaffold.base',
        version='1.0.0',
        docTypes=['hazardous_special_scheme'],
        label='脚手架工程',
        role='third_level',
        familyKey='hazardous_special_scheme',
        tier='3',
        disciplineTags=['scaffold'],
        extractorIds=['project_facts', 'hazard_facts'],
        ruleIds=[
            'scaffold_structure_parameters_completeness',
            'scaffold_safety_device_and_wall_tie_completeness',
            'scaffold_monitoring_and_acceptance_completeness',
        ],
        evidencePackIds=['scaffold.base'],
        defaultEnabled=False,
        description='脚手架工程 type pack，补充结构参数、连墙件/防坠落装置和监测验收检查。',
        readiness='ready',
        promotionCriteria={
            'ruleCoverage': True,
            'policyEvidenceReady': True,
            'testsReady': True,
            'versionedCasesReady': True,
        },
    )
