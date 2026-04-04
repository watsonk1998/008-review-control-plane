from __future__ import annotations

from src.review.rules.packs.construction_scheme import get_construction_scheme_base_pack
from src.review.rules.packs.construction_org import get_construction_org_base_pack
from src.review.rules.packs.gas_area_ops import get_gas_area_ops_pack
from src.review.rules.packs.hazardous_special_scheme import get_hazardous_special_scheme_base_pack
from src.review.rules.packs.hot_work import get_hot_work_pack
from src.review.rules.packs.lifting_operations import get_lifting_operations_pack
from src.review.rules.packs.review_support_material import get_review_support_material_base_pack
from src.review.rules.packs.supervision_plan import get_supervision_plan_base_pack
from src.review.rules.packs.temporary_power import get_temporary_power_pack
from src.review.schema import PolicyPack


_BASE_PACKS = {
    'construction_org': 'construction_org.base',
    'construction_scheme': 'construction_scheme.base',
    'hazardous_special_scheme': 'hazardous_special_scheme.base',
    'supervision_plan': 'supervision_plan.base',
    'review_support_material': 'review_support_material.base',
}

_SCENARIO_TAGS = {
    'lifting_operations': 'lifting_operations.base',
    'temporary_power': 'temporary_power.base',
    'hot_work': 'hot_work.base',
    'gas_area_ops': 'gas_area_ops.base',
    'special_equipment': 'special_equipment.base',
    'working_at_height': 'working_at_height.base',
}
def _make_scenario_pack(pack_id: str, discipline_tag: str) -> PolicyPack:
    return PolicyPack(
        id=pack_id,
        version='1.0.0',
        docTypes=['construction_org', 'hazardous_special_scheme', 'construction_scheme'],
        disciplineTags=[discipline_tag],
        extractorIds=['hazard_facts'],
        ruleIds=[],
        evidencePackIds=[],
        defaultEnabled=False,
        description=f'Scenario pack for {discipline_tag}.',
        readiness='placeholder',
    )


def get_policy_pack_registry() -> dict[str, PolicyPack]:
    registry = {
        'construction_org.base': get_construction_org_base_pack(),
        'hazardous_special_scheme.base': get_hazardous_special_scheme_base_pack(),
        'construction_scheme.base': get_construction_scheme_base_pack(),
        'supervision_plan.base': get_supervision_plan_base_pack(),
        'review_support_material.base': get_review_support_material_base_pack(),
        'lifting_operations.base': get_lifting_operations_pack(),
        'temporary_power.base': get_temporary_power_pack(),
        'hot_work.base': get_hot_work_pack(),
        'gas_area_ops.base': get_gas_area_ops_pack(),
    }
    for discipline_tag, pack_id in _SCENARIO_TAGS.items():
        if pack_id in registry:
            continue
        registry[pack_id] = _make_scenario_pack(pack_id, discipline_tag)
    return registry


def select_policy_packs(document_type: str, discipline_tags: list[str], requested_pack_ids: list[str] | None = None) -> list[PolicyPack]:
    registry = get_policy_pack_registry()
    selected_ids: list[str] = []
    base_pack_id = _BASE_PACKS.get(document_type)
    if base_pack_id and base_pack_id in registry:
        selected_ids.append(base_pack_id)
    for tag in discipline_tags:
        pack_id = _SCENARIO_TAGS.get(tag)
        pack = registry.get(pack_id) if pack_id else None
        if pack and _pack_supports_document_type(pack, document_type) and pack_id not in selected_ids:
            selected_ids.append(pack_id)
    for pack_id in requested_pack_ids or []:
        pack = registry.get(pack_id)
        if pack and _pack_supports_document_type(pack, document_type) and pack_id not in selected_ids:
            selected_ids.append(pack_id)
    return [registry[pack_id] for pack_id in selected_ids]


def _pack_supports_document_type(pack: PolicyPack, document_type: str) -> bool:
    return not pack.docTypes or document_type in pack.docTypes
