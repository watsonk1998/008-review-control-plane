from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.domain.models import TaskRecord
from src.orchestrator.deepresearch_runtime import DeepResearchRuntime
from src.repositories.sqlite_store import SQLiteTaskStore
from src.services.document_loader import DocumentLoader
from src.services.fixture_service import FixtureService


class FakeLLM:
    async def summarize_chunks(self, query, chunks, extra_instruction=''):
        return {'content': f'SUMMARY::{query}::{len(chunks)}', 'raw': {}, 'usage': None}

    async def chat(self, messages, temperature=0.2, max_tokens=1200):
        return {'content': '辅助审查要点\n- 示例\n\n非正式审查结论', 'raw': {}, 'usage': None}


class FakeFast:
    async def search_dataset_chunks(self, dataset_id, query, **kwargs):
        return {
            'mode': 'dataset',
            'datasetId': dataset_id,
            'collectionId': None,
            'query': query,
            'chunks': [
                {
                    'text': 'chunk-1',
                    'raw': {'q': 'chunk-1'},
                    'score': 0.92,
                    'sourceLabel': 'demo-source',
                    'mode': 'dataset',
                }
            ],
            'raw': {'data': {'list': [{'q': 'chunk-1'}]}},
            'meta': {'count': 1},
            'durationMs': 12,
        }

    async def search_collection_chunks(self, collection_id, query, dataset_id=None):
        raise AssertionError('collection mode should not be used in this test')


class FakeGPTResearcher:
    async def run_deep_research(self, query, *, use_web, source_urls=None):
        return {
            'report': f'RESEARCH::{query}::{use_web}',
            'sources': [{'title': 'source'}],
            'meta': {'reportType': 'deep'},
        }

    async def run_local_docs_research(self, query, document_paths):
        return {
            'report': f'LOCAL::{query}::{len(document_paths)}',
            'sources': [{'path': document_paths[0]}],
            'meta': {'reportType': 'detailed_report'},
        }


class FakeDeepTutor:
    async def ask_with_context(self, query, context_chunks):
        return {
            'answer': f'DEEPTUTOR::{query}::{len(context_chunks)}',
            'sources': {'rag': []},
            'transcript': [],
        }



def build_fixture_manifest(tmp_path: Path) -> Path:
    fixture_dir = tmp_path / 'fixtures'
    fixture_dir.mkdir()
    doc_path = fixture_dir / 'sample.md'
    doc_path.write_text('# 标题\n\n这里是测试文档。', encoding='utf-8')
    manifest = [
        {
            'id': 'sample-doc',
            'title': 'Sample Doc',
            'domain': 'supervision',
            'sourcePath': str(doc_path),
            'copiedPath': str(doc_path),
            'fileType': 'md',
            'notes': 'test fixture',
        }
    ]
    manifest_path = tmp_path / 'manifest.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')
    return manifest_path



def build_runtime(tmp_path: Path, deeptutor=None) -> tuple[DeepResearchRuntime, SQLiteTaskStore]:
    manifest_path = build_fixture_manifest(tmp_path)
    store = SQLiteTaskStore(tmp_path / 'runtime.sqlite')
    runtime = DeepResearchRuntime(
        store=store,
        fixture_service=FixtureService(manifest_path),
        document_loader=DocumentLoader(),
        llm_gateway=FakeLLM(),
        fast_adapter=FakeFast(),
        gpt_researcher=FakeGPTResearcher(),
        deeptutor=deeptutor,
        tasks_dir=tmp_path / 'artifacts',
    )
    return runtime, store



def create_task(**overrides) -> TaskRecord:
    now = datetime.now(timezone.utc)
    payload = {
        'id': 'task-1',
        'taskType': 'knowledge_qa',
        'capabilityMode': 'fast',
        'query': '施工组织设计应包含哪些安全内容？',
        'datasetId': None,
        'collectionId': None,
        'fixtureId': None,
        'useWeb': False,
        'debug': True,
        'sourceUrls': [],
        'status': 'created',
        'plan': None,
        'result': None,
        'error': None,
        'createdAt': now,
        'updatedAt': now,
    }
    payload.update(overrides)
    return TaskRecord(**payload)


async def test_runtime_knowledge_qa_fast_mode_uses_llm_summary(tmp_path: Path):
    runtime, store = build_runtime(tmp_path, deeptutor=None)
    task = create_task(capabilityMode='fast')
    store.create_task(task)

    await runtime.execute_task(task.id)

    saved = store.get_task(task.id)
    assert saved is not None
    assert saved.status == 'succeeded'
    assert saved.result is not None
    assert saved.result['capabilitiesUsed'] == ['fast', 'llm_gateway']
    assert saved.result['finalAnswer'].startswith('SUMMARY::')
    assert saved.result['sources'][0]['label'] == 'demo-source'
    assert len(store.list_events(task.id)) >= 4


async def test_runtime_review_assist_aggregates_fixture_and_deeptutor(tmp_path: Path):
    runtime, store = build_runtime(tmp_path, deeptutor=FakeDeepTutor())
    task = create_task(
        id='task-2',
        taskType='review_assist',
        capabilityMode='auto',
        query='请辅助审查该监理规划是否覆盖安全控制要点',
        fixtureId='sample-doc',
    )
    store.create_task(task)

    await runtime.execute_task(task.id)

    saved = store.get_task(task.id)
    assert saved is not None
    assert saved.status == 'succeeded'
    assert saved.result is not None
    assert 'deeptutor' in saved.result['capabilitiesUsed']
    assert 'llm_gateway' in saved.result['capabilitiesUsed']
    assert saved.result['notice'].startswith('这是辅助审查结果')
    assert len(saved.result['artifacts']) >= 2
