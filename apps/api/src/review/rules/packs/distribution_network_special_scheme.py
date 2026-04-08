from __future__ import annotations

from src.review.schema import PolicyPack


def get_distribution_network_special_scheme_base_pack() -> PolicyPack:
    return PolicyPack(
        id='distribution_network_special_scheme.base',
        version='1.0.0',
        docTypes=['distribution_network_special_scheme'],
        label='配网工程专项施工方案',
        role='base',
        familyKey='distribution_network_special_scheme',
        tier='2-family',
        disciplineTags=['power_outage_work'],
        extractorIds=['project_facts', 'hazard_facts', 'schedule_resource_facts'],
        ruleIds=[],
        evidencePackIds=[],
        defaultEnabled=True,
        description='配网工程专项施工方案二级基础 pack，承载专项族归属、三级专项挂载与后续共性规则扩展锚点。',
        readiness='ready',
        promotionCriteria={
            'ruleCoverage': True,
            'policyEvidenceReady': True,
            'testsReady': True,
            'versionedCasesReady': False,
        },
    )
