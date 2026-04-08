from __future__ import annotations

from src.review.schema import PolicyPack


def get_underground_excavation_pack() -> PolicyPack:
    return PolicyPack(
        id='underground_excavation.base',
        version='1.0.0',
        docTypes=['hazardous_special_scheme'],
        disciplineTags=['underground_excavation'],
        extractorIds=['project_facts', 'hazard_facts'],
        ruleIds=[
            'underground_excavation_water_control_completeness',
            'underground_excavation_support_parameters_completeness',
            'underground_excavation_monitoring_and_drawings',
        ],
        evidencePackIds=['underground_excavation.base', 'review.visibility'],
        defaultEnabled=False,
        description='暗挖工程 type pack，补充地下水控制、支护参数和监测图纸检查。',
        readiness='ready',
        promotionCriteria={
            'ruleCoverage': True,
            'policyEvidenceReady': True,
            'testsReady': True,
            'versionedCasesReady': True,
        },
    )
