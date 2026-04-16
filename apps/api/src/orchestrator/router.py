from __future__ import annotations

from src.review.rules.packs import select_policy_packs



def infer_review_document_type(query: str, fixture_title: str | None = None, requested_document_type: str | None = None) -> str:
    if requested_document_type:
        return requested_document_type
    text = f'{query} {fixture_title or ""}'
    if '配网' in text or ('停电施工作业' in text and '专项施工方案' in text):
        return 'distribution_network_special_scheme'
    if '专项施工方案' in text or '危大' in text:
        return 'hazardous_special_scheme'
    if '施工组织设计' in text or '施工组织' in text:
        return 'construction_org'
    if '施工方案' in text:
        return 'construction_scheme'
    if '监理' in text:
        return 'supervision_plan'
    return 'review_support_material'


_TAG_KEYWORDS = {
    'power_outage_work': ['停电施工作业'],
    'lifting_operations': ['吊装', '起重', '行车'],
    'temporary_power': ['临电', '施工用电', '停送电'],
    'hot_work': ['动火'],
    'gas_area_ops': ['煤气'],
    'special_equipment': ['特种设备', '行车'],
    'working_at_height': ['高处作业', '高空'],
}


def infer_review_discipline_tags(
    query: str,
    fixture_title: str | None = None,
    requested_discipline_tags: list[str] | None = None,
) -> list[str]:
    text = f'{query} {fixture_title or ""}'
    tags: list[str] = list(requested_discipline_tags or [])
    for tag, keywords in _TAG_KEYWORDS.items():
        if tag in tags:
            continue
        if any(keyword in text for keyword in keywords):
            tags.append(tag)
    return tags


def _normalize_discipline_tags_for_document_type(document_type: str, discipline_tags: list[str]) -> list[str]:
    normalized: list[str] = []
    for tag in discipline_tags:
        mapped = tag
        if document_type == 'hazardous_special_scheme' and tag == 'lifting_operations':
            mapped = 'lifting_installation_removal'
        if document_type == 'distribution_network_special_scheme' and tag == 'temporary_power':
            mapped = 'power_outage_work'
        if mapped not in normalized:
            normalized.append(mapped)
    return normalized


def choose_structured_review_profile(
    query: str,
    fixture_title: str | None = None,
    *,
    requested_document_type: str | None = None,
    requested_discipline_tags: list[str] | None = None,
    requested_policy_pack_ids: list[str] | None = None,
    requested_rule_pack_ids: list[str] | None = None,
    strict_mode: bool | None = None,
) -> dict[str, object]:
    document_type = infer_review_document_type(query, fixture_title, requested_document_type)
    discipline_tags = _normalize_discipline_tags_for_document_type(
        document_type,
        infer_review_discipline_tags(query, fixture_title, requested_discipline_tags),
    )
    hinted_packs = [
        pack.id
        for pack in select_policy_packs(
            document_type,
            discipline_tags,
            requested_pack_ids=[],
        )
        if pack.readiness == 'ready'
    ]
    return {
        'authority': 'provisional_router_hint',
        'requestedDocumentType': requested_document_type,
        'requestedDisciplineTags': requested_discipline_tags or [],
        'requestedPolicyPackIds': requested_policy_pack_ids or [],
        'requestedRulePackIds': requested_rule_pack_ids or [],
        'documentTypeHint': document_type,
        'disciplineTagHints': discipline_tags,
        'policyPackHints': hinted_packs,
        'rulePackHints': requested_rule_pack_ids or [],
        'strictMode': True if strict_mode is None else strict_mode,
    }


