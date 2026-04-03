from __future__ import annotations

from src.config.fastgpt import DEFAULT_DATASET_REGISTRY
from src.review.rules.packs import select_policy_packs


def infer_default_dataset(query: str, task_type: str, requested_dataset_id: str | None = None) -> str | None:
    if requested_dataset_id:
        return requested_dataset_id
    if any(keyword in query for keyword in ['条例', '法律', '法规']):
        return DEFAULT_DATASET_REGISTRY['laws_regulations']['datasetId']
    if any(keyword in query for keyword in ['监理', '施工组织', '施组', '市政', '建筑', '专项施工方案', '危大']):
        return DEFAULT_DATASET_REGISTRY['building_municipal']['datasetId']
    if task_type in {'review_assist', 'structured_review'}:
        return DEFAULT_DATASET_REGISTRY['building_municipal']['datasetId']
    return DEFAULT_DATASET_REGISTRY['gb_national']['datasetId']


def infer_review_document_type(query: str, fixture_title: str | None = None, requested_document_type: str | None = None) -> str:
    if requested_document_type:
        return requested_document_type
    text = f'{query} {fixture_title or ""}'
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


def choose_structured_review_profile(
    query: str,
    fixture_title: str | None = None,
    *,
    requested_document_type: str | None = None,
    requested_discipline_tags: list[str] | None = None,
    requested_policy_pack_ids: list[str] | None = None,
    strict_mode: bool | None = None,
) -> dict[str, object]:
    document_type = infer_review_document_type(query, fixture_title, requested_document_type)
    discipline_tags = infer_review_discipline_tags(query, fixture_title, requested_discipline_tags)
    selected_packs = [
        pack.id
        for pack in select_policy_packs(
            document_type,
            discipline_tags,
            requested_pack_ids=requested_policy_pack_ids or [],
        )
    ]
    return {
        'authority': 'provisional_router_hint',
        'requestedDocumentType': requested_document_type,
        'requestedDisciplineTags': requested_discipline_tags or [],
        'requestedPolicyPackIds': requested_policy_pack_ids or [],
        'documentTypeHint': document_type,
        'disciplineTagHints': discipline_tags,
        'policyPackHints': selected_packs,
        'strictMode': True if strict_mode is None else strict_mode,
    }


def choose_capability_chain(task_type: str, capability_mode: str, has_fixture: bool) -> list[str]:
    if task_type == 'knowledge_qa':
        if capability_mode == 'fast':
            return ['fast', 'llm_gateway']
        if capability_mode == 'llm_only':
            return ['llm_gateway']
        if capability_mode == 'gpt_researcher':
            return ['gpt_researcher']
        return ['fast', 'deeptutor', 'llm_gateway']
    if task_type == 'deep_research':
        return ['gpt_researcher', 'llm_gateway']
    if task_type == 'document_research':
        return ['gpt_researcher', 'llm_gateway']
    if task_type == 'review_assist':
        chain = ['fast', 'deeptutor', 'llm_gateway']
        if has_fixture:
            chain.insert(2, 'gpt_researcher')
        return chain
    if task_type == 'structured_review':
        return ['structured_review_executor', 'llm_gateway']
    return ['llm_gateway']
