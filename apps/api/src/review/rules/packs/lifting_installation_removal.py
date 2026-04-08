from __future__ import annotations

from src.review.schema import PolicyPack


def get_lifting_installation_removal_pack() -> PolicyPack:
    return PolicyPack(
        id='lifting_installation_removal.base',
        version='1.0.0',
        docTypes=['hazardous_special_scheme'],
        label='起重吊装及安装拆卸',
        role='third_level',
        familyKey='hazardous_special_scheme',
        tier='3',
        disciplineTags=['lifting_installation_removal'],
        extractorIds=['project_facts', 'hazard_facts'],
        ruleIds=[
            'lifting_installation_removal_scheme_integrity',
            'lifting_installation_removal_site_bearing_traceability',
            'lifting_installation_removal_temporary_fixation_completeness',
            'lifting_installation_removal_drawing_visibility',
        ],
        evidencePackIds=['lifting_installation_removal.base', 'review.visibility'],
        defaultEnabled=False,
        description='起重吊装及安装拆卸工程 type pack，补充方案骨架、站位承载、临时固定和图纸可视域检查。',
        readiness='ready',
        promotionCriteria={
            'ruleCoverage': True,
            'policyEvidenceReady': True,
            'testsReady': True,
            'versionedCasesReady': True,
        },
    )
