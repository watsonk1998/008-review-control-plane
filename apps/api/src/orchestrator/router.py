from __future__ import annotations

from src.config.fastgpt import DEFAULT_DATASET_REGISTRY


def infer_default_dataset(query: str, task_type: str, requested_dataset_id: str | None = None) -> str | None:
    if requested_dataset_id:
        return requested_dataset_id
    text = query.lower()
    if any(keyword in query for keyword in ['条例', '法律', '法规']):
        return DEFAULT_DATASET_REGISTRY['laws_regulations']['datasetId']
    if any(keyword in query for keyword in ['监理', '施工组织', '施组', '市政', '建筑']):
        return DEFAULT_DATASET_REGISTRY['building_municipal']['datasetId']
    if task_type == 'review_assist':
        return DEFAULT_DATASET_REGISTRY['building_municipal']['datasetId']
    return DEFAULT_DATASET_REGISTRY['gb_national']['datasetId']


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
    return ['llm_gateway']
