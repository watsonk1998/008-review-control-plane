from __future__ import annotations

from src.review.schema import PolicyPack


def get_construction_org_base_pack() -> PolicyPack:
    return PolicyPack(
        id='construction_org.base',
        version='1.0.0',
        docTypes=['construction_org'],
        disciplineTags=['electromechanical', 'lifting_operations', 'temporary_power', 'hot_work', 'gas_area_ops', 'special_equipment'],
        extractorIds=['project_facts', 'hazard_facts', 'schedule_resource_facts'],
        ruleIds=[
            'construction_org_structure_completeness',
            'construction_org_duplicate_sections',
            'construction_org_attachment_visibility',
            'construction_org_special_scheme_gap',
            'construction_org_emergency_plan_targeted',
            'construction_org_shutdown_resource_conflict',
        ],
        evidencePackIds=['construction_org.base', 'hazardous_special_scheme.base', 'review.visibility', 'review.emergency'],
        defaultEnabled=True,
        description='施工组织设计基础 pack，覆盖结构完整性、危大挂接、附件可视域和资源窗口冲突。',
        readiness='ready',
    )
