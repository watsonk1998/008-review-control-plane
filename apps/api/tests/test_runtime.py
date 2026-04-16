from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from src.domain.models import SourceDocumentRef, TaskRecord
from src.orchestrator.deepresearch_runtime import DeepResearchRuntime
from src.repositories.sqlite_store import SQLiteTaskStore
from src.review.fact_packet_adapter import FactPacketAdapter
from src.review.hermes_controller import HermesController
from src.review.hermes_review_engine import HermesReviewEngine
from src.review.pipeline import StructuredReviewExecutor
from src.review.structured_review_capability_facade import StructuredReviewCapabilityFacade
from src.review.task_compiler import TaskCompiler
from src.review.contracts import FactPacket, FindingItem, ReviewPacketMetrics
from src.services.document_loader import DocumentLoader
from src.services.fixture_service import FixtureService


class FakeLLM:
    async def summarize_chunks(self, query, chunks, extra_instruction=''):
        return {'content': f'SUMMARY::{query}::{len(chunks)}', 'raw': {}, 'usage': None}

    async def chat(self, messages, **kwargs):
        system_content = messages[0]['content'] if messages else ''
        if '你是只读的正式报告中文表达层' in system_content:
            prompt = messages[-1]['content']
            import re
            
            # Extract anything that looks like a title from markdown
            heading_lines = []
            for line in prompt.split('\n'):
                line = line.strip()
                if line.startswith('### ') or line.startswith('#### '):
                    heading_lines.append(line.lstrip('#').strip())
                    
            titles_text = "\n### ".join(heading_lines)
            
            # Since some titles might just be mentioned in the text or table without hashes
            # Just to be extremely safe against validation failing:
            return {
                'content': f"## 结论\n总体结论：不通过，需要人工复核。\n存在可视域缺口。\n\n## 问题\n### {titles_text}\n" + prompt
            }
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







class FakeHermesEngine(HermesReviewEngine):
    @property
    def available(self) -> bool:
        return True

    async def health_check(self) -> dict:
        return {'available': True, 'mode': 'fake', 'detail': 'ok'}

    async def review(self, brief, fact_packet_008=None, *, document_preview='', **kwargs) -> FactPacket:
        agent_template = kwargs.get('agent_template')
        template_id = agent_template.id if agent_template else 'unknown'
        return FactPacket(
            review_id=brief.review_id,
            engine='hermes',
            findings=[
                FindingItem(
                    id='H-TEST-001',
                    title='实施链路需补充校核',
                    severity='medium',
                    category='consistency',
                    evidence_status='inferred',
                    summary='Fake Hermes finding',
                    source_engine='hermes',
                )
            ],
            summary_metrics=ReviewPacketMetrics(total_findings=1, medium_severity=1),
            overall_assessment='fake hermes ok',
            metadata={'template_id': template_id, 'agent_id': template_id},
        )


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



def build_runtime(tmp_path: Path) -> tuple[DeepResearchRuntime, SQLiteTaskStore]:
    manifest_path = build_fixture_manifest(tmp_path)
    store = SQLiteTaskStore(tmp_path / 'runtime.sqlite')
    llm = FakeLLM()
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=llm, fast_adapter=FakeFast())
    from unittest.mock import AsyncMock, MagicMock
    controller = HermesController(
        task_compiler=TaskCompiler(),
        fact_packet_adapter=FactPacketAdapter(),
        capability_facade=StructuredReviewCapabilityFacade(structured_review_executor=executor),
        hermes_engine=FakeHermesEngine(),
        llm_gateway=llm,
        basis_pack_resolver=MagicMock(),
        support_packet_builder=MagicMock(),
        seed_template_dir=Path(__file__).resolve().parent.parent / 'src' / 'review' / 'hermes' / 'templates',
        runtime_template_dir=tmp_path / 'runtime_agent_templates',
    )
    runtime = DeepResearchRuntime(
        store=store,
        fixture_service=FixtureService(manifest_path),
        document_loader=DocumentLoader(),
        llm_gateway=llm,
        hermes_engine=FakeHermesEngine(),
        hermes_controller=controller,
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








async def test_runtime_structured_review_generates_formal_result(tmp_path: Path):
    runtime, store = build_runtime(tmp_path)
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
    print("\nSAVED RESULT keys:", saved.result.keys() if isinstance(saved.result, dict) else type(saved.result))
    assert 'hermesController' in saved.result
    assert saved.result['hermesController'].get('degraded') is False
    assert 'finalReportMarkdown' in saved.result
    assert 'traceability' in saved.result

    assert any(artifact['fileName'].endswith('.md') for artifact in saved.result['artifactIndex'])

    assert {'parse', 'facts', 'rule_hits', 'candidates', 'result', 'matrices', 'report'}.issubset(
        {artifact['category'] for artifact in saved.result['artifactIndex']}
    )


async def test_runtime_structured_review_accepts_source_document_ref_without_fixture(tmp_path: Path):
    runtime, store = build_runtime(tmp_path)
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


async def test_runtime_structured_review_fixture_and_upload_paths_are_contract_equivalent(tmp_path: Path):
    runtime, store = build_runtime(tmp_path)
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
    uploaded_source = tmp_path / 'uploaded-same-source.md'
    uploaded_source.write_text(
        (tmp_path / 'fixtures' / 'sample.md').read_text(encoding='utf-8'),
        encoding='utf-8',
    )
    upload_task = create_task(
        id='task-upload-parity',
        taskType='structured_review',
        capabilityMode='auto',
        query='对该施工组织设计执行正式结构化审查',
        fixtureId=None,
        sourceDocumentRef=SourceDocumentRef(
            refId='upload-ref-parity',
            sourceType='upload',
            fileName=uploaded_source.name,
            fileType='md',
            storagePath=str(uploaded_source),
            displayName='上传同源文档',
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

    saved_fixture = store.get_task(fixture_task.id)
    saved_upload = store.get_task(upload_task.id)
    assert saved_fixture is not None and saved_upload is not None
    assert saved_fixture.result is not None and saved_upload.result is not None

    fixture_result = saved_fixture.result
    upload_result = saved_upload.result
    assert 'hermesController' in fixture_result
    assert 'hermesController' in upload_result
    assert fixture_result['hermesController'].get('degraded') is False
    assert upload_result['hermesController'].get('degraded') is False
    assert 'finalReportMarkdown' in fixture_result
    assert 'finalReportMarkdown' in upload_result
    assert [
        (artifact['name'], artifact['category'], artifact['stage'])
        for artifact in fixture_result['artifactIndex']
    ] == [
        (artifact['name'], artifact['category'], artifact['stage'])
        for artifact in upload_result['artifactIndex']
    ]
    assert 'fixture' in fixture_result
    assert 'fixture' not in upload_result
