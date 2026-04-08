from __future__ import annotations

from src.review.schema import PolicyPack


def get_steel_structure_installation_pack() -> PolicyPack:
    return PolicyPack(
        id='steel_structure_installation.base',
        version='1.0.0',
        docTypes=['hazardous_special_scheme'],
        label='钢结构安装',
        role='third_level',
        familyKey='hazardous_special_scheme',
        tier='3',
        disciplineTags=['steel_structure_installation'],
        extractorIds=['project_facts', 'hazard_facts'],
        ruleIds=[
            'steel_structure_installation_structure_completeness',
            'steel_structure_installation_lifting_scheme_integrity',
            'steel_structure_installation_support_and_unloading',
            'steel_structure_installation_drawing_and_acceptance',
        ],
        evidencePackIds=['steel_structure_installation.base', 'review.visibility'],
        defaultEnabled=False,
        description='钢结构安装工程 type pack，补充吊装方案完整性、临时支撑/卸载条件与图纸验收检查。',
        readiness='ready',
        promotionCriteria={
            'ruleCoverage': True,
            'policyEvidenceReady': True,
            'testsReady': True,
            'versionedCasesReady': True,
        },
    )
