from __future__ import annotations

from src.review.schema import PolicyPack


def get_power_outage_work_pack() -> PolicyPack:
    return PolicyPack(
        id='power_outage_work.base',
        version='1.0.0',
        docTypes=['distribution_network_special_scheme'],
        label='停电施工作业',
        role='third_level',
        familyKey='distribution_network_special_scheme',
        tier='3',
        disciplineTags=['power_outage_work'],
        extractorIds=['hazard_facts', 'schedule_resource_facts'],
        ruleIds=['power_outage_work_structure_completeness', 'temporary_power_control_linkage'],
        evidencePackIds=['power_outage_work.base', 'review.emergency'],
        defaultEnabled=False,
        description='停电施工作业三级专项 pack，承载停电施工作业专项结构要求，并复用停送电控制链路检查。',
        readiness='ready',
        promotionCriteria={
            'ruleCoverage': True,
            'policyEvidenceReady': True,
            'testsReady': True,
            'versionedCasesReady': False,
        },
    )
