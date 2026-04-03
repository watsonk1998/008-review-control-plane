from __future__ import annotations

from src.review.schema import PolicyPack


def get_hazardous_special_scheme_base_pack() -> PolicyPack:
    return PolicyPack(
        id='hazardous_special_scheme.base',
        version='1.0.0',
        docTypes=['hazardous_special_scheme'],
        disciplineTags=['lifting_operations', 'temporary_power', 'hot_work', 'gas_area_ops', 'special_equipment', 'working_at_height'],
        extractorIds=['project_facts', 'hazard_facts', 'schedule_resource_facts'],
        ruleIds=[
            'hazardous_special_scheme_core_sections',
            'hazardous_special_scheme_attachment_visibility',
            'hazardous_special_scheme_calculation_evidence',
            'hazardous_special_scheme_emergency_targeted',
            'hazardous_special_scheme_measure_linkage',
        ],
        evidencePackIds=['hazardous_special_scheme.base', 'review.visibility', 'review.emergency'],
        defaultEnabled=True,
        description='危大专项方案基础 pack，覆盖核心章节、验算证据、风险措施与应急闭环。',
    )
