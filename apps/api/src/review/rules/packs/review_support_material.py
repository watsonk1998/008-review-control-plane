from __future__ import annotations

from src.review.schema import PolicyPack


def get_review_support_material_base_pack() -> PolicyPack:
    return PolicyPack(
        id='review_support_material.base',
        version='1.0.0',
        docTypes=['review_support_material'],
        extractorIds=['project_facts'],
        ruleIds=[
            'review_support_material_context_only',
            'review_support_material_attachment_visibility',
        ],
        evidencePackIds=['review_support_material.base', 'review.visibility'],
        defaultEnabled=True,
        description='审查辅助材料基础 pack，显式提示其只能补充背景、不能替代正式方案正文。',
        readiness='ready',
        promotionCriteria={
            'ruleCoverage': True,
            'policyEvidenceReady': True,
            'testsReady': True,
            'versionedCasesReady': True,
        },
    )
