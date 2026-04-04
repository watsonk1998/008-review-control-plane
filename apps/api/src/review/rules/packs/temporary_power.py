from __future__ import annotations

from src.review.schema import PolicyPack


def get_temporary_power_pack() -> PolicyPack:
    return PolicyPack(
        id='temporary_power.base',
        version='1.0.0',
        docTypes=['construction_org', 'construction_scheme'],
        disciplineTags=['temporary_power'],
        extractorIds=['hazard_facts', 'schedule_resource_facts'],
        ruleIds=['temporary_power_control_linkage'],
        evidencePackIds=['hazardous_special_scheme.base', 'review.emergency'],
        defaultEnabled=False,
        description='临时用电/停送电场景 pack，检查控制措施与应急安排是否成链。',
        readiness='ready',
        promotionCriteria={
            'ruleCoverage': True,
            'policyEvidenceReady': True,
            'testsReady': True,
            'versionedCasesReady': False,
        },
    )
