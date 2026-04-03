from __future__ import annotations

from src.review.rules.packs.construction_org import get_construction_org_base_pack
from src.review.schema import PolicyPack


_DISCIPLINE_TAGS = {
    'lifting_operations': 'lifting_operations.base',
    'temporary_power': 'temporary_power.base',
    'hot_work': 'hot_work.base',
    'gas_area_ops': 'gas_area_ops.base',
    'special_equipment': 'special_equipment.base',
}


def _make_scenario_pack(pack_id: str, discipline_tag: str) -> PolicyPack:
    return PolicyPack(
        id=pack_id,
        version='0.1.0',
        docTypes=['construction_org'],
        disciplineTags=[discipline_tag],
        extractorIds=[],
        ruleIds=[],
        evidencePackIds=[],
        defaultEnabled=False,
    )


def get_policy_pack_registry() -> dict[str, PolicyPack]:
    registry = {
        'construction_org.base': get_construction_org_base_pack(),
    }
    for discipline_tag, pack_id in _DISCIPLINE_TAGS.items():
        registry[pack_id] = _make_scenario_pack(pack_id, discipline_tag)
    return registry


def select_policy_packs(document_type: str, discipline_tags: list[str]) -> list[PolicyPack]:
    registry = get_policy_pack_registry()
    selected: list[PolicyPack] = []
    if document_type == 'construction_org':
        selected.append(registry['construction_org.base'])
    for tag in discipline_tags:
        pack_id = _DISCIPLINE_TAGS.get(tag)
        if pack_id and pack_id in registry:
            selected.append(registry[pack_id])
    return selected
