from __future__ import annotations

from src.review.schema import PolicyPack


def get_manual_bored_pile_pack() -> PolicyPack:
    return PolicyPack(
        id='manual_bored_pile.base',
        version='1.0.0',
        docTypes=['hazardous_special_scheme'],
        disciplineTags=['manual_bored_pile'],
        extractorIds=['project_facts', 'hazard_facts'],
        ruleIds=[
            'manual_bored_pile_jump_excavation_integrity',
            'manual_bored_pile_gas_and_electric_safety_completeness',
            'manual_bored_pile_forbidden_conditions_manual_review',
        ],
        evidencePackIds=['manual_bored_pile.base', 'review.visibility'],
        defaultEnabled=False,
        description='人工挖孔桩工程 type pack，补充跳挖、防中毒触电与禁用条件人工复核检查。',
        readiness='ready',
        promotionCriteria={
            'ruleCoverage': True,
            'policyEvidenceReady': True,
            'testsReady': True,
            'versionedCasesReady': True,
        },
    )
