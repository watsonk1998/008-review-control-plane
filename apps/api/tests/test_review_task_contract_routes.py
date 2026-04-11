from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from src.domain.models import SourceDocumentRef, TaskArtifact, TaskEvent, TaskRecord
from src.main import app
from src.routes import review_reports as review_reports_route
from src.routes import review_task_contracts
from src.routes import review_tasks as review_tasks_route


def _make_upload(tmp_path: Path, file_id: str, file_name: str = 'target.md') -> Path:
    upload_dir = tmp_path / file_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    path = upload_dir / file_name
    path.write_text('# demo\n', encoding='utf-8')
    return path


def test_compile_review_task_request_maps_frontend_contract_to_internal_request(monkeypatch, tmp_path: Path):
    target_path = _make_upload(tmp_path, 'target-1')
    basis_path = _make_upload(tmp_path, 'basis-1', 'basis.md')
    monkeypatch.setattr(review_task_contracts, 'get_settings', lambda: SimpleNamespace(uploads_dir=tmp_path))

    request = review_task_contracts.CreateReviewTaskRequest.model_validate(
        {
            'classification': {
                'l1': 'special_scheme_review',
                'l2': 'distribution_network_special_scheme',
                'l3': ['temporary_power', 'execution_continuity'],
            },
            'documents': {
                'target_file_ids': ['target-1'],
                'basis_file_ids': ['basis-1'],
                'project_context_file_ids': [],
            },
            'builtin_asset_selections': {
                'standard_ids': ['gb50016'],
                'template_ids': ['structured_review_primary_worker'],
                'rule_pack_ids': ['power_outage_work.base'],
            },
            'review_intent': {
                'enabled_modules': ['structure_completeness', 'execution_continuity'],
                'disabled_modules': ['evidence_validation'],
                'focus_requirements': ['重点检查停送电链路闭环'],
            },
            'metadata': {'source': 'test', 'debug': False},
        }
    )

    internal_request, plan_seed = review_task_contracts.compile_create_task_request(request)
    assert internal_request.sourceDocumentRef is not None
    assert internal_request.sourceDocumentRef.refId == 'target-1'
    assert internal_request.sourceDocumentRef.storagePath == str(target_path)
    assert internal_request.policyPackIds == ['power_outage_work.base']
    assert internal_request.documentType == 'distribution_network_special_scheme'
    assert internal_request.disciplineTags == ['temporary_power', 'execution_continuity']
    assert '停送电链路闭环' in internal_request.query
    assert plan_seed['hermesInput']['basisFiles'][0]['path'] == str(basis_path)
    assert 'structured_review_primary_worker' in plan_seed['hermesInput']['enabledAgents']
    assert 'visibility_gap_reviewer' in plan_seed['hermesInput']['disabledAgents']


def test_review_task_create_route_returns_frozen_contract(monkeypatch, tmp_path: Path):
    target_path = _make_upload(tmp_path, 'target-1')
    monkeypatch.setattr(review_task_contracts, 'get_settings', lambda: SimpleNamespace(uploads_dir=tmp_path))
    now = datetime.now(timezone.utc)

    class FakeStore:
        def __init__(self):
            self.plan = None

        def update_task(self, task_id: str, **fields):
            self.plan = fields['plan']
            return TaskRecord(
                id=task_id,
                taskType='structured_review',
                capabilityMode='auto',
                query='query',
                sourceDocumentRef=SourceDocumentRef(
                    refId='target-1',
                    sourceType='upload',
                    fileName='target.md',
                    fileType='md',
                    storagePath=str(target_path),
                    displayName='target.md',
                ),
                documentType='distribution_network_special_scheme',
                disciplineTags=['temporary_power'],
                strictMode=True,
                policyPackIds=['power_outage_work.base'],
                status='created',
                plan=fields['plan'],
                createdAt=now,
                updatedAt=now,
            )

    class FakeService:
        def __init__(self):
            self.store = FakeStore()
            self.created = None
            self.scheduled = None

        def create_task(self, request):
            self.created = request
            return TaskRecord(
                id='task-frontend-1',
                taskType='structured_review',
                capabilityMode='auto',
                query=request.query,
                sourceDocumentRef=request.sourceDocumentRef,
                documentType=request.documentType,
                disciplineTags=request.disciplineTags or [],
                strictMode=True,
                policyPackIds=request.policyPackIds or [],
                status='created',
                createdAt=now,
                updatedAt=now,
            )

        def schedule_task(self, task_id: str):
            self.scheduled = task_id

    fake_service = FakeService()
    monkeypatch.setattr(review_tasks_route, 'get_task_service', lambda: fake_service)
    client = TestClient(app)

    response = client.post(
        '/api/review-tasks',
        json={
            'classification': {'l1': 'special_scheme_review', 'l2': 'distribution_network_special_scheme', 'l3': ['temporary_power']},
            'documents': {'target_file_ids': ['target-1'], 'basis_file_ids': [], 'project_context_file_ids': []},
            'builtin_asset_selections': {'standard_ids': [], 'template_ids': [], 'rule_pack_ids': ['power_outage_work.base']},
            'review_intent': {'enabled_modules': ['structure_completeness'], 'disabled_modules': [], 'focus_requirements': ['重点检查闭环']},
            'metadata': {'source': 'mock-frontend', 'debug': False},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload['task_id'] == 'task-frontend-1'
    assert payload['status'] == 'created'
    assert payload['review_brief_id'] == 'task-frontend-1'
    assert payload['links']['status'].endswith('/api/review-tasks/task-frontend-1')
    assert fake_service.created.sourceDocumentRef is not None
    assert fake_service.created.documentType == 'distribution_network_special_scheme'
    assert fake_service.scheduled == 'task-frontend-1'
    assert fake_service.store.plan['hermesInput']['frontendSelections']['metadata']['source'] == 'mock-frontend'


def test_review_task_status_and_result_routes_map_internal_state(monkeypatch):
    now = datetime.now(timezone.utc)
    task = TaskRecord(
        id='task-status-1',
        taskType='structured_review',
        capabilityMode='auto',
        query='query',
        sourceDocumentRef=SourceDocumentRef(refId='r1', sourceType='upload', fileName='target.md', fileType='md', storagePath='/tmp/target.md', displayName='target.md'),
        documentType='distribution_network_special_scheme',
        disciplineTags=['temporary_power'],
        strictMode=True,
        policyPackIds=['power_outage_work.base'],
        status='succeeded',
        plan={'hermesInput': {'frontendSelections': {'review_intent': {'enabled_modules': ['structure_completeness', 'execution_continuity'], 'disabled_modules': []}}}},
        result={
            'summary': {'overallConclusion': '文档存在结构性问题'},
            'issues': [
                {'id': 'ISSUE-1', 'title': '章节缺失', 'summary': '缺少章节', 'layer': 'L1', 'severity': 'high', 'manualReviewNeeded': False, 'evidenceMissing': False, 'issueKind': 'hard_defect', 'recommendation': ['补齐章节']},
                {'id': 'ISSUE-2', 'title': '停送电链路存在遗漏', 'summary': '链路闭环不足', 'layer': 'L2', 'severity': 'medium', 'manualReviewNeeded': False, 'evidenceMissing': False, 'issueKind': 'hard_defect', 'recommendation': ['补充闭环']},
            ],
            'artifactIndex': [
                {'name': 'report', 'fileName': 'hermes-controller-final-report.md', 'mediaType': 'text/markdown', 'sizeBytes': 12, 'downloadUrl': '/api/tasks/task-status-1/artifacts/hermes-controller-final-report.md', 'category': 'report', 'stage': 'result', 'primary': True}
            ],
            'finalReportPacket': {
                'key_findings': [{'id': 'ISSUE-1', 'title': '章节缺失', 'severity': 'high', 'summary': '缺少章节', 'suggestion': '补齐章节', 'raw_data': {'module_name': 'structure_completeness', 'ownership': 'support_material'}}],
                'all_findings': [
                    {'id': 'ISSUE-1', 'title': '章节缺失', 'severity': 'high', 'summary': '缺少章节', 'suggestion': '补齐章节', 'raw_data': {'module_name': 'structure_completeness', 'ownership': 'support_material'}},
                    {'id': 'ISSUE-2', 'title': '停送电链路存在遗漏', 'severity': 'medium', 'summary': '链路闭环不足', 'suggestion': '补充闭环', 'raw_data': {'module_name': 'execution_continuity', 'ownership': 'hermes_main_review'}},
                ],
                'traceability': [{'issue_id': 'ISSUE-1'}],
                'executive_summary': 'Hermes 裁决认为文档存在结构性问题',
                'metadata': {
                    'decision_owner': 'hermes',
                    'support_owner': 'structured_review_capability_facade',
                    'final_output_entrypoint': 'hermes_review_assembler',
                },
            },
            'traceability': [{'issue_id': 'ISSUE-1'}],
            'finalAnswer': '文档存在结构性问题',
        },
        createdAt=now,
        updatedAt=now,
    )
    events = [TaskEvent(timestamp=now, stage='report', capability='structured_review', status='completed', message='Report generated')]
    artifacts = [TaskArtifact(name='report', fileName='hermes-controller-final-report.md', mediaType='text/markdown', sizeBytes=12, downloadUrl='/api/tasks/task-status-1/artifacts/hermes-controller-final-report.md', category='report', stage='result', primary=True)]

    class FakeService:
        def get_task(self, task_id: str):
            return task if task_id == task.id else None
        def get_task_events(self, task_id: str):
            return events
        def list_task_artifacts(self, task_id: str):
            return artifacts

    monkeypatch.setattr(review_tasks_route, 'get_task_service', lambda: FakeService())
    client = TestClient(app)

    status_response = client.get('/api/review-tasks/task-status-1')
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload['status'] == 'completed'
    assert status_payload['progress_stage'] == 'done'
    assert status_payload['report_id'] == 'task-status-1'

    result_response = client.get('/api/review-tasks/task-status-1/result')
    assert result_response.status_code == 200
    result_payload = result_response.json()
    assert result_payload['report_id'] == 'task-status-1'
    assert result_payload['summary']['risk_level'] == 'high'
    assert result_payload['summary']['overall_conclusion'] == 'Hermes 裁决认为文档存在结构性问题'
    assert result_payload['modules']['structure_completeness']['findings'][0]['id'] == 'ISSUE-1'
    assert result_payload['modules']['execution_continuity']['findings'][0]['id'] == 'ISSUE-2'
    assert result_payload['export_links']['markdown'].endswith('hermes-controller-final-report.md')
    assert result_payload['metadata']['assembler'] == 'HermesReviewAssembler'
    assert result_payload['metadata']['decision_owner'] == 'hermes'
    assert result_payload['metadata']['support_owner'] == 'structured_review_capability_facade'
    assert result_payload['metadata']['result_ownership'] == 'hermes_decision_layer'
    assert result_payload['metadata']['module_bucketing'] == 'execution_metadata_first'
    assert result_payload['metadata']['support_material_present'] is True


def test_review_task_events_stream_emits_frozen_event_types(monkeypatch):
    now = datetime.now(timezone.utc)
    task = TaskRecord(
        id='task-stream-1',
        taskType='structured_review',
        capabilityMode='auto',
        query='query',
        sourceDocumentRef=SourceDocumentRef(refId='r1', sourceType='upload', fileName='target.md', fileType='md', storagePath='/tmp/target.md', displayName='target.md'),
        documentType='distribution_network_special_scheme',
        disciplineTags=['temporary_power'],
        strictMode=True,
        policyPackIds=['power_outage_work.base'],
        status='succeeded',
        result={'summary': {'overallConclusion': 'done'}},
        createdAt=now,
        updatedAt=now,
    )
    events = [TaskEvent(timestamp=now, stage='report', capability='structured_review', status='completed', message='Report generated')]
    artifacts = [TaskArtifact(name='report', fileName='report.json', mediaType='application/json', sizeBytes=12, downloadUrl='/api/tasks/task-stream-1/artifacts/report.json', category='result', stage='result', primary=True)]

    class FakeService:
        def get_task(self, task_id: str):
            return task if task_id == task.id else None
        def get_task_events(self, task_id: str):
            return events
        def list_task_artifacts(self, task_id: str):
            return artifacts

    monkeypatch.setattr(review_tasks_route, 'get_task_service', lambda: FakeService())
    client = TestClient(app)

    with client.stream('GET', '/api/review-tasks/task-stream-1/events') as response:
        assert response.status_code == 200
        payload = ''.join(response.iter_text())

    assert 'event: task_created' in payload
    assert 'event: progress' in payload
    assert 'event: artifact_ready' in payload
    assert 'event: completed' in payload
    assert 'task-stream-1' in payload


def test_review_report_feedback_route_accepts_feedback(monkeypatch):
    class FakeService:
        def submit_report_feedback(self, *, report_id: str, feedback_type: str, comment=None, source=None):
            assert report_id == 'task-1'
            assert feedback_type == 'helpful'
            return {'id': 'fb-1'}

    monkeypatch.setattr(review_reports_route, 'get_task_service', lambda: FakeService())
    client = TestClient(app)
    response = client.post('/api/review-reports/task-1/feedback', json={'feedback_type': 'helpful', 'comment': 'ok'})
    assert response.status_code == 200
    assert response.json() == {'accepted': True, 'report_id': 'task-1', 'feedback_id': 'fb-1'}


def test_review_task_result_ownership_prefers_decision_sources():
    now = datetime.now(timezone.utc)
    task = TaskRecord(
        id='task-decision-owned-1',
        taskType='structured_review',
        capabilityMode='auto',
        query='query',
        sourceDocumentRef=SourceDocumentRef(refId='r1', sourceType='upload', fileName='target.md', fileType='md', storagePath='/tmp/target.md', displayName='target.md'),
        documentType='distribution_network_special_scheme',
        disciplineTags=[],
        strictMode=True,
        policyPackIds=[],
        status='succeeded',
        plan={'hermesInput': {'frontendSelections': {'review_intent': {'enabled_modules': ['structure_completeness'], 'disabled_modules': []}}}},
        result={
            'summary': {'overallConclusion': 'support says pass'},
            'issues': [{'id': 'SUP-1', 'title': 'support issue', 'summary': 'support issue', 'severity': 'low', 'recommendation': ['support rec']}],
            'finalReportPacket': {
                'executive_summary': 'Hermes decision says revise',
                'key_findings': [{'id': 'DEC-1', 'title': 'decision issue', 'severity': 'medium', 'summary': 'decision issue', 'suggestion': 'decision rec', 'raw_data': {'module_name': 'structure_completeness', 'ownership': 'hermes_main_review'}}],
                'all_findings': [{'id': 'DEC-1', 'title': 'decision issue', 'severity': 'medium', 'summary': 'decision issue', 'suggestion': 'decision rec', 'raw_data': {'module_name': 'structure_completeness', 'ownership': 'hermes_main_review'}}],
                'metadata': {},
            },
            'hermesController': {'mainReviewOutcomes': []},
        },
        createdAt=now,
        updatedAt=now,
    )
    payload = review_task_contracts.build_review_task_result(task, [])
    assert payload.summary.overall_conclusion == 'Hermes decision says revise'
    assert payload.key_findings[0]['id'] == 'DEC-1'
    assert payload.modules['structure_completeness'].findings[0]['id'] == 'DEC-1'
    assert payload.recommendations == ['decision rec']


def test_module_bucketing_prefers_execution_metadata_over_heuristics():
    now = datetime.now(timezone.utc)
    task = TaskRecord(
        id='task-module-metadata-1',
        taskType='structured_review',
        capabilityMode='auto',
        query='query',
        sourceDocumentRef=SourceDocumentRef(refId='r1', sourceType='upload', fileName='target.md', fileType='md', storagePath='/tmp/target.md', displayName='target.md'),
        documentType='distribution_network_special_scheme',
        disciplineTags=[],
        strictMode=True,
        policyPackIds=[],
        status='succeeded',
        plan={'hermesInput': {'frontendSelections': {'review_intent': {'enabled_modules': ['legality_compliance', 'execution_continuity'], 'disabled_modules': []}}}},
        result={
            'issues': [
                {
                    'id': 'ISSUE-META-1',
                    'title': '停送电链路存在遗漏',
                    'summary': '标题会被启发式误判到执行连续性',
                    'severity': 'medium',
                    'recommendation': ['补齐规范条款'],
                }
            ],
            'finalReportPacket': {
                'all_findings': [
                    {
                        'id': 'ISSUE-META-1',
                        'title': '停送电链路存在遗漏',
                        'severity': 'medium',
                        'summary': '来自裁决层的模块归属',
                        'suggestion': '补齐规范条款',
                        'raw_data': {'module_name': 'legality_compliance', 'ownership': 'hermes_main_review'},
                    }
                ],
                'key_findings': [
                    {
                        'id': 'ISSUE-META-1',
                        'title': '停送电链路存在遗漏',
                        'severity': 'medium',
                        'summary': '来自裁决层的模块归属',
                        'suggestion': '补齐规范条款',
                        'raw_data': {'module_name': 'legality_compliance', 'ownership': 'hermes_main_review'},
                    }
                ],
            },
            'hermesController': {'mainReviewOutcomes': []},
        },
        createdAt=now,
        updatedAt=now,
    )
    payload = review_task_contracts.build_review_task_result(task, [])
    assert payload.modules['legality_compliance'].findings[0]['id'] == 'ISSUE-META-1'
    assert payload.modules['execution_continuity'].findings == []
