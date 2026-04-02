from __future__ import annotations

from src.domain.models import TaskRecord
from src.orchestrator.router import choose_capability_chain, infer_default_dataset


class TaskPlanner:
    def build_plan(self, task: TaskRecord, has_fixture: bool) -> dict:
        dataset_id = infer_default_dataset(task.query, task.taskType, task.datasetId)
        capability_chain = choose_capability_chain(task.taskType, task.capabilityMode, has_fixture)
        notes: list[str] = []
        if task.collectionId:
            notes.append('用户指定了 collectionId，优先尝试 Fast 模式 B。')
        if task.sourceUrls:
            notes.append('用户提供了 sourceUrls，可在没有搜索 API key 时为 GPT Researcher 提供外部来源。')
        if task.taskType == 'deep_research' and not task.useWeb and not task.sourceUrls:
            notes.append('deep_research 未启用 useWeb，建议通过 sourceUrls 或 fixture 提供来源。')
        return {
            'goal': f"Route {task.taskType} through DeepResearchAgent compatibility runtime",
            'taskType': task.taskType,
            'requestedCapabilityMode': task.capabilityMode,
            'resolvedDatasetId': dataset_id,
            'capabilityChain': capability_chain,
            'routingNotes': notes,
            'execution': [
                {'stage': 'plan', 'owner': 'deepresearch_runtime'},
                *[
                    {'stage': f'exec_{index + 1}', 'owner': capability}
                    for index, capability in enumerate(capability_chain)
                ],
                {'stage': 'finalize', 'owner': 'deepresearch_runtime'},
            ],
            'boundary': {
                'deepresearchagent': 'planner/router/coordinator only, not the final domain reviewer',
                'deeptutor': 'knowledge explanation service',
                'gpt_researcher': 'research/report generation service',
                'fastgpt': 'chunk retrieval layer first, not answer black-box',
            },
        }
