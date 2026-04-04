from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from src.adapters.gpt_researcher_adapter import GPTResearcherAdapter
from src.domain.models import SourceDocumentRef, TaskRecord
from src.orchestrator.deepresearch_runtime import DeepResearchRuntime
from src.repositories.sqlite_store import SQLiteTaskStore
from src.services.document_loader import DocumentLoader
from src.services.fixture_service import FixtureService


class FakeLLM:
    async def summarize_chunks(self, query, chunks, extra_instruction=''):
        return {'content': f'SUMMARY::{query}::{len(chunks)}', 'raw': {}, 'usage': None}

    async def chat(self, messages, temperature=0.2, max_tokens=1200):
        return {'content': '辅助审查要点\n- 示例\n\n非正式审查结论', 'raw': {}, 'usage': None}

    def explain_issue_candidates(self, candidates):
        return [
            {
                'id': f'ISSUE-{index + 1:03d}',
                'title': candidate.title,
                'layer': candidate.layerHint,
                'severity': candidate.severityHint,
                'findingType': candidate.findingType,
                'summary': candidate.title,
                'manualReviewNeeded': candidate.manualReviewNeeded,
                'evidenceMissing': candidate.evidenceMissing,
                'manualReviewReason': candidate.manualReviewReason,
                'docEvidence': [span.model_dump(mode='json') for span in candidate.docEvidence],
                'policyEvidence': [span.model_dump(mode='json') for span in candidate.policyEvidence],
                'recommendation': ['demo'],
                'confidence': 'medium',
                'whetherManualReviewNeeded': candidate.manualReviewNeeded,
            }
            for index, candidate in enumerate(candidates)
        ]


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
    doc_path.write_text('# 施工组织设计\n\n## 第一节 工程概况\n项目名称：测试项目\n项目编号：P0-TEST\n## 第五节 防火安全\n保持消防器材完好。\n## 第七节 防火安全\n重复章节用于回归测试。\n施工单台行车停机改造时间为7天。\n起重吊装 作业\n施工用电 作业\n动火作业\n附件2：施工总平面布置图\n', encoding='utf-8')
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
        'sourceDocumentRef': None,
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


class FakeSourceURLResearcher:
    last_instance = None

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.conduct_called = False
        self.ext_context = None
        FakeSourceURLResearcher.last_instance = self

    async def conduct_research(self):
        self.conduct_called = True

    async def write_report(self, ext_context=None):
        self.ext_context = ext_context
        return f"REPORT::{self.kwargs['report_type']}::{self.kwargs['report_source']}"

    def get_research_sources(self):
        return [{'title': 'live-source'}]


async def test_gpt_researcher_source_urls_use_static_context(monkeypatch):
    adapter = GPTResearcherAdapter(external_path='/tmp/unused')

    def fake_prepare_import():
        return (
            FakeSourceURLResearcher,
            SimpleNamespace(
                ResearchReport=SimpleNamespace(value='research_report'),
                DeepResearch=SimpleNamespace(value='deep_research'),
            ),
            SimpleNamespace(
                Static=SimpleNamespace(value='static'),
                Web=SimpleNamespace(value='web'),
            ),
            SimpleNamespace(Analytical='analytical'),
        )

    async def fake_build_source_url_context(source_urls):
        assert source_urls == ['https://example.com/a']
        return 'STATIC_CONTEXT', [{'url': source_urls[0], 'preview': 'demo'}]

    monkeypatch.setattr(adapter, '_prepare_import', fake_prepare_import)
    monkeypatch.setattr(adapter, '_build_source_url_context', fake_build_source_url_context)

    result = await adapter.run_deep_research(
        '比较三种能力的角色差异',
        use_web=False,
        source_urls=['https://example.com/a'],
    )

    assert result['meta']['reportSource'] == 'static_source_urls'
    assert result['meta']['sourceUrlCount'] == 1
    assert result['sources'][0]['url'] == 'https://example.com/a'
    assert FakeSourceURLResearcher.last_instance is not None
    assert FakeSourceURLResearcher.last_instance.conduct_called is False
    assert FakeSourceURLResearcher.last_instance.ext_context == 'STATIC_CONTEXT'


async def test_runtime_structured_review_generates_formal_result(tmp_path: Path):
    runtime, store = build_runtime(tmp_path, deeptutor=None)
    task = create_task(
        id='task-3',
        taskType='structured_review',
        capabilityMode='auto',
        query='对该施工组织设计执行正式结构化审查',
        fixtureId='sample-doc',
        documentType='construction_org',
        disciplineTags=['lifting_operations', 'temporary_power', 'hot_work'],
        strictMode=True,
        policyPackIds=['construction_org.base'],
    )
    store.create_task(task)

    await runtime.execute_task(task.id)

    saved = store.get_task(task.id)
    assert saved is not None
    assert saved.status == 'succeeded'
    assert saved.result is not None
    assert saved.result['summary']['documentType'] == 'construction_org'
    assert saved.result['resolvedProfile']['documentType'] == 'construction_org'
    assert saved.result['resolvedProfile']['strictMode'] is True
    assert 'construction_org.base' in saved.result['resolvedProfile']['policyPackIds']
    assert saved.result['summary']['manualReviewNeeded'] is True
    assert saved.result['summary']['visibilitySummary']['manualReviewNeeded'] is True
    assert saved.result['visibility']['manualReviewNeeded'] is True
    assert any(issue['title'] == '附件处于可视域缺口，需人工复核原件' for issue in saved.result['issues'])
    attachment_issue = next(issue for issue in saved.result['issues'] if issue['title'] == '附件处于可视域缺口，需人工复核原件')
    assert attachment_issue['manualReviewNeeded'] is True
    assert attachment_issue['manualReviewReason'] == 'visibility_gap'
    assert any(path.endswith('.md') for path in saved.result['artifacts'])
    assert any(artifact['fileName'].endswith('.md') for artifact in saved.result['artifactIndex'])
    assert {'construction_org.base', 'lifting_operations.base', 'temporary_power.base', 'hot_work.base'}.issubset(
        set(saved.result['summary']['selectedPacks'])
    )
    assert saved.result['summary']['selectedPacks'] == saved.result['resolvedProfile']['policyPackIds']
    assert {'parse', 'facts', 'rule_hits', 'candidates', 'result', 'matrices', 'report'}.issubset(
        {artifact['category'] for artifact in saved.result['artifactIndex']}
    )


async def test_runtime_structured_review_accepts_source_document_ref_without_fixture(tmp_path: Path):
    runtime, store = build_runtime(tmp_path, deeptutor=None)
    source_document = tmp_path / 'uploaded-structured-review.md'
    source_document.write_text(
        '# 施工组织设计\n\n'
        '## 第一节 工程概况\n项目名称：上传测试项目\n项目编号：UPLOAD-P0\n'
        '## 第五节 防火安全\n保持消防器材完好。\n'
        '## 第七节 防火安全\n重复章节用于回归测试。\n'
        '起重吊装 作业\n施工用电 作业\n动火作业\n'
        '附件2：施工总平面布置图\n',
        encoding='utf-8',
    )
    task = create_task(
        id='task-4',
        taskType='structured_review',
        capabilityMode='auto',
        query='对上传文档执行正式结构化审查',
        fixtureId=None,
        sourceDocumentRef=SourceDocumentRef(
            refId='upload-ref-1',
            sourceType='upload',
            fileName=source_document.name,
            fileType='md',
            storagePath=str(source_document),
            displayName='上传测试项目',
        ),
        documentType='construction_org',
        disciplineTags=['lifting_operations', 'temporary_power', 'hot_work'],
        strictMode=True,
        policyPackIds=['construction_org.base'],
    )
    store.create_task(task)

    await runtime.execute_task(task.id)

    saved = store.get_task(task.id)
    assert saved is not None
    assert saved.status == 'succeeded'
    assert saved.sourceDocumentRef is not None
    assert saved.sourceDocumentRef.sourceType == 'upload'
    assert saved.result is not None
    assert saved.result['summary']['documentType'] == 'construction_org'
    assert saved.result['summary']['manualReviewNeeded'] is True
    assert 'fixture' not in saved.result
    assert any(issue['title'] == '附件处于可视域缺口，需人工复核原件' for issue in saved.result['issues'])


async def test_runtime_structured_review_fixture_and_upload_stay_contract_equivalent(tmp_path: Path):
    runtime, store = build_runtime(tmp_path, deeptutor=None)

    fixture_task = create_task(
        id='task-fixture-parity',
        taskType='structured_review',
        capabilityMode='auto',
        query='对该施工组织设计执行正式结构化审查',
        fixtureId='sample-doc',
        documentType='construction_org',
        disciplineTags=['lifting_operations', 'temporary_power', 'hot_work'],
        strictMode=True,
        policyPackIds=['construction_org.base'],
    )
    upload_source = tmp_path / 'uploaded-structured-review.md'
    upload_source.write_text((tmp_path / 'fixtures' / 'sample.md').read_text(encoding='utf-8'), encoding='utf-8')
    upload_task = create_task(
        id='task-upload-parity',
        taskType='structured_review',
        capabilityMode='auto',
        query='对该施工组织设计执行正式结构化审查',
        fixtureId=None,
        sourceDocumentRef=SourceDocumentRef(
            refId='upload-ref-parity',
            sourceType='upload',
            fileName=upload_source.name,
            fileType='md',
            storagePath=str(upload_source),
            displayName='上传同构样本',
        ),
        documentType='construction_org',
        disciplineTags=['lifting_operations', 'temporary_power', 'hot_work'],
        strictMode=True,
        policyPackIds=['construction_org.base'],
    )
    store.create_task(fixture_task)
    store.create_task(upload_task)

    await runtime.execute_task(fixture_task.id)
    await runtime.execute_task(upload_task.id)

    fixture_saved = store.get_task(fixture_task.id)
    upload_saved = store.get_task(upload_task.id)
    assert fixture_saved is not None and upload_saved is not None
    assert fixture_saved.result is not None and upload_saved.result is not None

    assert fixture_saved.result['summary']['documentType'] == upload_saved.result['summary']['documentType']
    assert fixture_saved.result['resolvedProfile'] == upload_saved.result['resolvedProfile']
    assert fixture_saved.result['visibility'] == upload_saved.result['visibility']
    assert [issue['findingType'] for issue in fixture_saved.result['issues']] == [issue['findingType'] for issue in upload_saved.result['issues']]
    assert [(item['name'], item['category']) for item in fixture_saved.result['artifactIndex']] == [
        (item['name'], item['category']) for item in upload_saved.result['artifactIndex']
    ]
