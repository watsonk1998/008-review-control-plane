from __future__ import annotations

from src.review.schema import PolicyPack


def get_curtain_wall_installation_pack() -> PolicyPack:
    return PolicyPack(
        id='curtain_wall_installation.base',
        version='1.0.0',
        docTypes=['hazardous_special_scheme'],
        label='建筑幕墙安装',
        role='third_level',
        familyKey='hazardous_special_scheme',
        tier='3',
        disciplineTags=['curtain_wall_installation'],
        extractorIds=['project_facts', 'hazard_facts'],
        ruleIds=[
            'curtain_wall_installation_facility_integrity',
            'curtain_wall_installation_route_and_layout_completeness',
            'curtain_wall_installation_drawing_and_acceptance',
        ],
        evidencePackIds=['curtain_wall_installation.base', 'review.visibility'],
        defaultEnabled=False,
        description='建筑幕墙安装工程 type pack，补充安装设施、运输路线和平面图纸/验收检查。',
        readiness='ready',
        promotionCriteria={
            'ruleCoverage': True,
            'policyEvidenceReady': True,
            'testsReady': True,
            'versionedCasesReady': True,
        },
    )
