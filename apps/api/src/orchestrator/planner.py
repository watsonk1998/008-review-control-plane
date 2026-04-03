from __future__ import annotations

from src.domain.models import TaskRecord
from src.orchestrator.router import choose_capability_chain, choose_structured_review_profile, infer_default_dataset


class TaskPlanner:
    def build_plan(self, task: TaskRecord, has_fixture: bool, fixture_title: str | None = None) -> dict:
        dataset_id = infer_default_dataset(task.query, task.taskType, task.datasetId)
        capability_chain = choose_capability_chain(task.taskType, task.capabilityMode, has_fixture)
        notes: list[str] = []
        if task.collectionId:
            notes.append('用户指定了 collectionId，优先尝试 Fast 模式 B。')
        if task.sourceUrls:
            notes.append('用户提供了 sourceUrls，可在没有搜索 API key 时为 GPT Researcher 提供外部来源。')
        if task.taskType == 'deep_research' and not task.useWeb and not task.sourceUrls:
            notes.append('deep_research 未启用 useWeb，建议通过 sourceUrls 或 fixture 提供来源。')
        if task.taskType == 'structured_review' and not has_fixture:
            notes.append('structured_review 当前要求 fixtureId，以便进入结构化解析和证据归档流程。')

        execution = [
            {'stage': 'plan', 'owner': 'deepresearch_runtime'},
            *[
                {'stage': f'exec_{index + 1}', 'owner': capability}
                for index, capability in enumerate(capability_chain)
            ],
            {'stage': 'finalize', 'owner': 'deepresearch_runtime'},
        ]
        plan: dict[str, object] = {
            'goal': f'Route {task.taskType} through DeepResearchAgent compatibility runtime',
            'taskType': task.taskType,
            'requestedCapabilityMode': task.capabilityMode,
            'resolvedDatasetId': dataset_id,
            'capabilityChain': capability_chain,
            'routingNotes': notes,
            'execution': execution,
            'boundary': {
                'deepresearchagent': 'planner/router/coordinator only, not the final domain reviewer',
                'deeptutor': 'knowledge explanation service',
                'gpt_researcher': 'research/report generation service',
                'fastgpt': 'chunk retrieval layer first, not answer black-box',
            },
        }
        if task.taskType == 'structured_review':
            review_profile = choose_structured_review_profile(
                task.query,
                fixture_title,
                requested_document_type=task.documentType,
                requested_discipline_tags=task.disciplineTags,
                requested_policy_pack_ids=task.policyPackIds,
                strict_mode=task.strictMode,
            )
            notes.append('structured_review 的 reviewProfile 仅作为 provisional hints；最终 resolvedProfile 与 packs 由 review pipeline 生成。')
            plan['goal'] = 'Execute formal structured review through the review domain pipeline'
            plan['reviewProfile'] = review_profile
            plan['execution'] = [
                {'stage': 'plan', 'owner': 'deepresearch_runtime'},
                {'stage': 'parse', 'owner': 'review_parser'},
                {'stage': 'extract', 'owner': 'review_extractors'},
                {'stage': 'rules', 'owner': 'review_rule_engine'},
                {'stage': 'evidence', 'owner': 'review_evidence_builder'},
                {'stage': 'explain', 'owner': 'llm_gateway'},
                {'stage': 'report', 'owner': 'review_report_builder'},
                {'stage': 'finalize', 'owner': 'deepresearch_runtime'},
            ]
            plan['boundary'] = {
                **plan['boundary'],
                'structured_review': 'formal review domain pipeline in apps/api/src/review, runtime only orchestrates',
            }
        return plan
