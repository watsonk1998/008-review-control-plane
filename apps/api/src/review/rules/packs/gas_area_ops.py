from __future__ import annotations

from src.review.schema import PolicyPack


def get_gas_area_ops_pack() -> PolicyPack:
    return PolicyPack(
        id='gas_area_ops.base',
        version='1.0.0',
        docTypes=['construction_org', 'hazardous_special_scheme'],
        disciplineTags=['gas_area_ops'],
        extractorIds=['hazard_facts', 'schedule_resource_facts'],
        ruleIds=['gas_area_ops_control_linkage'],
        evidencePackIds=['hazardous_special_scheme.base', 'review.emergency'],
        defaultEnabled=False,
        description='煤气区域场景 pack，检查控制措施与中毒/窒息/爆炸类应急链路是否成链。',
        readiness='ready',
    )
