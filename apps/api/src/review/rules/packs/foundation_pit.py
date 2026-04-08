from __future__ import annotations

from src.review.schema import PolicyPack


def get_foundation_pit_pack() -> PolicyPack:
    return PolicyPack(
        id='foundation_pit.base',
        version='1.0.0',
        docTypes=['hazardous_special_scheme'],
        label='基坑工程',
        role='third_level',
        familyKey='hazardous_special_scheme',
        tier='3',
        disciplineTags=['foundation_pit'],
        extractorIds=['project_facts', 'hazard_facts'],
        ruleIds=[
            'foundation_pit_monitoring_and_drawings',
            'foundation_pit_support_sequence_integrity',
            'foundation_pit_acceptance_completeness',
        ],
        evidencePackIds=['foundation_pit.base', 'review.visibility'],
        defaultEnabled=False,
        description='基坑工程 type pack，补充支护/降水/开挖关系、监测图纸与验收章节检查。',
        readiness='ready',
        promotionCriteria={
            'ruleCoverage': True,
            'policyEvidenceReady': True,
            'testsReady': True,
            'versionedCasesReady': True,
        },
    )
