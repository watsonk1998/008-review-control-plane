from __future__ import annotations

from src.review.schema import PolicyPack


def get_power_outage_work_pack() -> PolicyPack:
    return PolicyPack(
        id='power_outage_work.base',
        version='1.0.0',
        docTypes=['distribution_network_special_scheme'],
        disciplineTags=['power_outage_work'],
        extractorIds=['hazard_facts', 'schedule_resource_facts'],
        ruleIds=['temporary_power_control_linkage'],
        evidencePackIds=['hazardous_special_scheme.base', 'review.emergency'],
        defaultEnabled=False,
        description='停电施工作业三级专项 pack，复用停送电控制链路检查并归属配网工程专项施工方案体系。',
        readiness='ready',
        promotionCriteria={
            'ruleCoverage': True,
            'policyEvidenceReady': True,
            'testsReady': True,
            'versionedCasesReady': False,
        },
    )
