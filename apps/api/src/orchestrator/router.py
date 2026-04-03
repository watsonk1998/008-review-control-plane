from __future__ import annotations

from src.config.fastgpt import DEFAULT_DATASET_REGISTRY
from src.review.rules.packs import select_policy_packs


def infer_default_dataset(query: str, task_type: str, requested_dataset_id: str | None = None) -> str | None:
    if requested_dataset_id:
        return requested_dataset_id
    if any(keyword in query for keyword in ['条例', '法律', '法规']):
        return DEFAULT_DATASET_REGISTRY['laws_regulations']['datasetId']
    if any(keyword in query for keyword in ['监理', '施工组织', '施组', '市政', '建筑']):
        return DEFAULT_DATASET_REGISTRY['building_municipal']['datasetId']
    if task_type in {'review_assist', 'structured_review'}:
        return DEFAULT_DATASET_REGISTRY['building_municipal']['datasetId']
    return DEFAULT_DATASET_REGISTRY['gb_national']['datasetId']


def infer_review_document_type(query: str, fixture_title: str | None = None) -> str:
    text = f'{query} {fixture_title or ""}'
    if '施工组织设计' in text or '施工组织' in text:
        return 'construction_org'
    if '专项施工方案' in text or '危大' in text:
        return 'hazardous_special_scheme'
    if '施工方案' in text:
        return 'construction_scheme'
    if '监理' in text:
        return 'supervision_plan'
    return 'review_support_material'


def infer_review_discipline_tags(query: str, fixture_title: str | None = None) -> list[str]:
    text = f'{query} {fixture_title or ""}'
    tags: list[str] = []
    if any(keyword in text for keyword in ['吊装', '起重', '行车']):
        tags.append('lifting_operations')
    if any(keyword in text for keyword in ['临电', '施工用电', '停送电']):
        tags.append('temporary_power')
    if '动火' in text:
        tags.append('hot_work')
    if '煤气' in text:
        tags.append('gas_area_ops')
    if any(keyword in text for keyword in ['特种设备', '行车']):
        tags.append('special_equipment')
    return tags


def choose_structured_review_profile(query: str, fixture_title: str | None = None) -> dict[str, object]:
    document_type = infer_review_document_type(query, fixture_title)
    discipline_tags = infer_review_discipline_tags(query, fixture_title)
    selected_packs = [pack.id for pack in select_policy_packs(document_type, discipline_tags)]
    return {
        'documentType': document_type,
        'disciplineTags': discipline_tags,
        'selectedPacks': selected_packs,
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
