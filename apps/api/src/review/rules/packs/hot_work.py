from __future__ import annotations

from src.review.schema import PolicyPack


def get_hot_work_pack() -> PolicyPack:
    return PolicyPack(
        id='hot_work.base',
        version='1.0.0',
        docTypes=['construction_org', 'construction_scheme'],
        disciplineTags=['hot_work'],
        extractorIds=['hazard_facts', 'schedule_resource_facts'],
        ruleIds=['hot_work_emergency_targeted'],
        evidencePackIds=['hazardous_special_scheme.base', 'review.emergency'],
        defaultEnabled=False,
        description='动火场景 pack，检查动火专项控制与火灾类应急安排是否匹配。',
        readiness='ready',
    )
