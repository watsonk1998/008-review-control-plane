from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from src.domain.models import CreateTaskRequest, SourceDocumentRef, TaskArtifact, TaskRecord
from src.main import app
from src.repositories.sqlite_store import SQLiteTaskStore
from src.routes import tasks as tasks_route
from src.routes import uploads as uploads_route
from src.services.task_service import TaskService


class StubRuntime:
    def __init__(self, tasks_dir: Path):
        self.tasks_dir = tasks_dir

    async def execute_task(self, task_id: str):
        return None


def test_task_service_persists_structured_review_fields_and_artifacts(tmp_path: Path):
    store = SQLiteTaskStore(tmp_path / 'service.sqlite')
    runtime = StubRuntime(tmp_path / 'artifacts')
    service = TaskService(store, runtime, runtime.tasks_dir)

    task = service.create_task(
        CreateTaskRequest(
            taskType='structured_review',
            capabilityMode='auto',
            query='执行危大专项方案正式审查',
            fixtureId='fixture-hz',
            documentType='hazardous_special_scheme',
            disciplineTags=['lifting_operations'],
            policyPackIds=['hazardous_special_scheme.base'],
        )
    )

    saved = store.get_task(task.id)
    assert saved is not None
    assert saved.documentType == 'hazardous_special_scheme'
    assert saved.disciplineTags == ['lifting_operations']
    assert saved.policyPackIds == ['hazardous_special_scheme.base']
    assert saved.strictMode is True

    artifact_dir = runtime.tasks_dir / task.id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / 'structured-review-report.md'
    artifact_path.write_text('# report', encoding='utf-8')

    artifacts = service.list_task_artifacts(task.id)
    assert len(artifacts) == 1
    assert artifacts[0].downloadUrl == f'/api/tasks/{task.id}/artifacts/structured-review-report.md'
    assert service.resolve_task_artifact(task.id, '../structured-review-report.md') == artifact_path.resolve()


def test_task_service_prefers_result_artifact_catalog_over_directory_scan(tmp_path: Path):
    store = SQLiteTaskStore(tmp_path / 'service.sqlite')
    runtime = StubRuntime(tmp_path / 'artifacts')
    service = TaskService(store, runtime, runtime.tasks_dir)

    task = service.create_task(
        CreateTaskRequest(
            taskType='structured_review',
            capabilityMode='auto',
            query='执行正式结构化审查',
            fixtureId='fixture-1',
            documentType='construction_org',
        )
    )

    task_dir = runtime.tasks_dir / task.id
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / 'unexpected-debug.json').write_text('{"debug": true}', encoding='utf-8')
    catalog_artifact = {
        'name': 'report',
        'fileName': 'structured-review-report.md',
        'mediaType': 'text/markdown',
        'sizeBytes': 12,
        'downloadUrl': f'/api/tasks/{task.id}/artifacts/structured-review-report.md',
        'category': 'report',
        'stage': 'report',
        'primary': True,
    }
    store.update_task(task.id, result={'artifactIndex': [catalog_artifact]})

    artifacts = service.list_task_artifacts(task.id)
    assert [artifact.fileName for artifact in artifacts] == ['structured-review-report.md']
    assert artifacts[0].category == 'report'
    assert artifacts[0].primary is True


def test_task_service_treats_explicit_empty_artifact_index_as_authoritative(tmp_path: Path):
    store = SQLiteTaskStore(tmp_path / 'service.sqlite')
    runtime = StubRuntime(tmp_path / 'artifacts')
    service = TaskService(store, runtime, runtime.tasks_dir)

    task = service.create_task(
        CreateTaskRequest(
            taskType='structured_review',
            capabilityMode='auto',
            query='执行正式结构化审查',
            fixtureId='fixture-1',
            documentType='construction_org',
        )
    )

    task_dir = runtime.tasks_dir / task.id
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / 'unexpected-debug.json').write_text('{"debug": true}', encoding='utf-8')
    store.update_task(task.id, result={'artifactIndex': []})

    artifacts = service.list_task_artifacts(task.id)
    assert artifacts == []


def test_task_service_derives_consistent_reviewer_task_state(tmp_path: Path):
    store = SQLiteTaskStore(tmp_path / 'service.sqlite')
    runtime = StubRuntime(tmp_path / 'artifacts')
    service = TaskService(store, runtime, runtime.tasks_dir)

    task = service.create_task(
        CreateTaskRequest(
            taskType='structured_review',
            capabilityMode='auto',
            query='执行正式结构化审查',
            fixtureId='fixture-1',
            documentType='construction_org',
        )
    )
    store.update_task(
        task.id,
        result={
            'summary': {
                'overallConclusion': 'demo',
                'documentType': 'construction_org',
                'selectedPacks': ['construction_org.base'],
                'manualReviewNeeded': True,
                'issueCount': 1,
                'layerCounts': {'L1': 1},
                'stats': {},
                'visibilitySummary': {
                    'attachmentCount': 1,
                    'counts': {'attachment_unparsed': 1},
                    'duplicateSectionTitles': [],
                    'parseWarnings': [],
                    'reasonCounts': {'title_detected_without_attachment_body': 1},
                    'manualReviewNeeded': True,
                },
            },
            'visibility': {
                'attachmentCount': 1,
                'counts': {'attachment_unparsed': 1},
                'duplicateSectionTitles': [],
                'parseWarnings': [],
                'reasonCounts': {'title_detected_without_attachment_body': 1},
                'manualReviewNeeded': True,
                'parserLimited': False,
                'fileType': 'md',
            },
            'resolvedProfile': {
                'requestedDocumentType': 'construction_org',
                'requestedDisciplineTags': [],
                'requestedPolicyPackIds': [],
                'documentType': 'construction_org',
                'disciplineTags': [],
                'policyPackIds': ['construction_org.base'],
                'strictMode': True,
            },
            'issues': [
                {
                    'id': 'ISSUE-001',
                    'title': '附件处于可视域缺口，需人工复核原件',
                    'layer': 'L1',
                    'severity': 'medium',
                    'findingType': 'visibility_gap',
                    'summary': '附件处于可视域缺口，需人工复核原件',
                    'manualReviewNeeded': True,
                    'evidenceMissing': True,
                    'manualReviewReason': 'visibility_gap',
                    'docEvidence': [],
                    'policyEvidence': [],
                    'recommendation': [],
                    'confidence': 'medium',
                }
            ],
            'matrices': {
                'hazardIdentification': {'values': {}},
                'ruleHits': [],
                'conflicts': {'values': {}},
                'attachmentVisibility': [
                    {
                        'id': 'attachment-1',
                        'attachmentNumber': '1',
                        'title': '附件1',
                        'visibility': 'attachment_unparsed',
                        'parseState': 'attachment_unparsed',
                        'manualReviewNeeded': True,
                        'reason': 'title_detected_without_attachment_body',
                        'referenceBlockIds': [],
                        'titleBlockId': None,
                    }
                ],
                'sectionStructure': [],
                'issueLayerCounts': {'L1': 1},
            },
            'artifactIndex': [],
            'reportMarkdown': '# demo',
            'artifacts': [],
            'unresolvedFacts': [],
            'capabilitiesUsed': ['llm_gateway'],
            'finalAnswer': 'demo',
        },
    )

    rejected = service.update_reviewer_decision(
        task.id,
        {
            'taskState': 'accepted',
            'note': 'checked',
            'issues': [{'issueId': 'ISSUE-001', 'state': 'confirmed', 'note': 'real defect'}],
            'attachments': [{'attachmentId': 'attachment-1', 'state': 'needs_attachment', 'note': 'need original'}],
        },
    )
    assert rejected.reviewerDecision is not None
    assert rejected.reviewerDecision.taskState == 'rejected'

    needs_attachment = service.update_reviewer_decision(
        task.id,
        {
            'taskState': 'accepted',
            'note': 'checked',
            'issues': [{'issueId': 'ISSUE-001', 'state': 'dismissed', 'note': 'not applicable'}],
            'attachments': [{'attachmentId': 'attachment-1', 'state': 'needs_attachment', 'note': 'need original'}],
        },
    )
    assert needs_attachment.reviewerDecision is not None
    assert needs_attachment.reviewerDecision.taskState == 'needs_attachment'

    accepted = service.update_reviewer_decision(
        task.id,
        {
            'taskState': 'pending',
            'note': 'checked',
            'issues': [{'issueId': 'ISSUE-001', 'state': 'dismissed', 'note': 'not applicable'}],
            'attachments': [{'attachmentId': 'attachment-1', 'state': 'dismissed', 'note': 'seen'}],
        },
    )
    assert accepted.reviewerDecision is not None
    assert accepted.reviewerDecision.taskState == 'accepted'


def test_sqlite_store_tolerates_malformed_structured_review_json_columns(tmp_path: Path):
    store = SQLiteTaskStore(tmp_path / 'service.sqlite')
    runtime = StubRuntime(tmp_path / 'artifacts')
    service = TaskService(store, runtime, runtime.tasks_dir)

    task = service.create_task(
        CreateTaskRequest(
            taskType='structured_review',
            capabilityMode='auto',
            query='执行正式结构化审查',
            fixtureId='fixture-1',
            documentType='construction_org',
        )
    )

    with store._connect() as conn:  # noqa: SLF001 - targeted persistence compatibility test
        conn.execute(
            '''
            UPDATE tasks
            SET source_document_ref_json = ?, reviewer_decision_json = ?, plan_json = ?
            WHERE id = ?
            ''',
            (
                '{"refId":',
                '{"taskState":"accepted","issues":"oops"}',
                '{bad-json',
                task.id,
            ),
        )

    restored = store.get_task(task.id)
    assert restored is not None
    assert restored.sourceDocumentRef is None
    assert restored.reviewerDecision is None
    assert restored.plan is None


def test_task_routes_legacy_structured_review_result_keeps_read_only_compatibility(monkeypatch, tmp_path: Path):
    now = datetime.now(timezone.utc)
    artifact_path = tmp_path / 'report.json'
    artifact_path.write_text('{"ok": true}', encoding='utf-8')

    class FakeService:
        def __init__(self):
            self.last_request = None

        def create_task(self, request):
            self.last_request = request
            return TaskRecord(
                id='task-route-1',
                taskType=request.taskType,
                capabilityMode=request.capabilityMode,
                query=request.query,
                fixtureId=request.fixtureId,
                sourceDocumentRef=request.sourceDocumentRef,
                sourceUrls=[],
                documentType=request.documentType,
                disciplineTags=request.disciplineTags or [],
                strictMode=request.strictMode,
                policyPackIds=request.policyPackIds or [],
                status='created',
                createdAt=now,
                updatedAt=now,
            )

        def schedule_task(self, task_id: str):
            return None

        def get_task(self, task_id: str):
            return TaskRecord(
                id=task_id,
                taskType='structured_review',
                capabilityMode='auto',
                query='query',
                fixtureId='fixture-1',
                sourceDocumentRef=SourceDocumentRef(
                    refId='fixture-1',
                    sourceType='fixture',
                    fileName='fixture.docx',
                    fileType='docx',
                    storagePath='/tmp/fixture.docx',
                    fixtureId='fixture-1',
                ),
                sourceUrls=[],
                documentType='construction_org',
                disciplineTags=['lifting_operations'],
                strictMode=True,
                policyPackIds=['construction_org.base'],
                status='succeeded',
                result={
                    'summary': {
                        'overallConclusion': 'demo',
                        'documentType': 'construction_org',
                        'selectedPacks': ['construction_org.base'],
                        'manualReviewNeeded': True,
                        'issueCount': 1,
                        'layerCounts': {'L1': 1},
                        'stats': {},
                        'visibilitySummary': {
                            'attachmentCount': 1,
                            'counts': {'attachment_unparsed': 1},
                            'duplicateSectionTitles': [],
                            'parseWarnings': [],
                            'reasonCounts': {'title_detected_without_attachment_body': 1},
                            'manualReviewNeeded': True,
                        },
                    },
                    'resolvedProfile': {
                        'requestedDocumentType': 'construction_org',
                        'requestedDisciplineTags': ['lifting_operations'],
                        'requestedPolicyPackIds': ['construction_org.base'],
                        'documentType': 'construction_org',
                        'disciplineTags': ['lifting_operations'],
                        'policyPackIds': ['construction_org.base'],
                        'strictMode': True,
                    },
                    'issues': [
                        {
                            'id': 'ISSUE-001',
                            'title': '附件处于可视域缺口，需人工复核原件',
                            'layer': 'L1',
                            'severity': 'medium',
                            'findingType': 'visibility_gap',
                            'summary': '附件处于可视域缺口，需人工复核原件',
                            'manualReviewNeeded': True,
                            'evidenceMissing': True,
                            'manualReviewReason': 'visibility_gap',
                            'docEvidence': [],
                            'policyEvidence': [],
                            'recommendation': [],
                            'confidence': 'medium',
                        }
                    ],
                    'matrices': {
                        'hazardIdentification': {'values': {}},
                        'ruleHits': [],
                        'conflicts': {'values': {}},
                        'attachmentVisibility': [],
                        'sectionStructure': [],
                        'issueLayerCounts': {'L1': 1},
                    },
                    'artifactIndex': [
                        {
                            'name': 'report',
                            'fileName': 'report.json',
                            'mediaType': 'application/json',
                            'sizeBytes': artifact_path.stat().st_size,
                            'downloadUrl': f'/api/tasks/{task_id}/artifacts/report.json',
                            'category': 'result',
                            'stage': 'result',
                            'primary': True,
                        }
                    ],
                    'reportMarkdown': '# demo',
                    'artifacts': ['report.json'],
                    'unresolvedFacts': [],
                    'capabilitiesUsed': ['llm_gateway'],
                    'finalAnswer': 'demo',
                },
                createdAt=now,
                updatedAt=now,
            )

        def get_task_events(self, task_id: str):
            return []

        def list_task_artifacts(self, task_id: str):
            return [
                TaskArtifact(
                    name='report',
                    fileName='report.json',
                    mediaType='application/json',
                    sizeBytes=artifact_path.stat().st_size,
                    downloadUrl=f'/api/tasks/{task_id}/artifacts/report.json',
                    category='result',
                    stage='result',
                    primary=True,
                )
            ]

        def resolve_task_artifact(self, task_id: str, artifact_name: str):
            assert artifact_name == 'report.json'
            return artifact_path

    fake_service = FakeService()
    monkeypatch.setattr(tasks_route, 'get_task_service', lambda: fake_service)
    client = TestClient(app)

    response = client.post(
        '/api/tasks',
        json={
            'taskType': 'structured_review',
            'capabilityMode': 'auto',
            'query': '执行正式结构化审查',
            'fixtureId': 'fixture-1',
            'documentType': 'construction_org',
            'disciplineTags': ['lifting_operations'],
            'strictMode': True,
            'policyPackIds': ['construction_org.base'],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload['documentType'] == 'construction_org'
    assert payload['disciplineTags'] == ['lifting_operations']
    assert payload['policyPackIds'] == ['construction_org.base']
    assert fake_service.last_request is not None
    assert fake_service.last_request.documentType == 'construction_org'
    assert payload['sourceDocumentRef'] is None

    artifacts_response = client.get('/api/tasks/task-route-1/artifacts')
    assert artifacts_response.status_code == 200
    assert artifacts_response.json()[0]['downloadUrl'].endswith('/report.json')

    download_response = client.get('/api/tasks/task-route-1/artifacts/report.json')
    assert download_response.status_code == 200
    assert download_response.text == '{"ok": true}'

    result_response = client.get('/api/tasks/task-route-1/result')
    assert result_response.status_code == 200
    result_payload = result_response.json()['result']
    assert result_payload['visibility']['attachmentCount'] == 1
    assert result_payload['visibility']['parseWarnings'] == []
    assert result_payload['issues'][0]['manualReviewNeeded'] is True
    assert result_payload['issues'][0]['whetherManualReviewNeeded'] is True
    assert result_payload['artifactIndex'] == artifacts_response.json()


def test_task_routes_fresh_structured_review_result_uses_canonical_visibility_only(monkeypatch):
    now = datetime.now(timezone.utc)

    class FakeService:
        def get_task(self, task_id: str):
            return TaskRecord(
                id=task_id,
                taskType='structured_review',
                capabilityMode='auto',
                query='query',
                fixtureId='fixture-1',
                sourceDocumentRef=None,
                sourceUrls=[],
                documentType='construction_org',
                disciplineTags=['lifting_operations'],
                strictMode=True,
                policyPackIds=['construction_org.base'],
                status='succeeded',
                result={
                    'summary': {
                        'overallConclusion': 'demo',
                        'documentType': 'construction_org',
                        'selectedPacks': ['construction_org.base'],
                        'manualReviewNeeded': True,
                        'issueCount': 1,
                        'layerCounts': {'L1': 1},
                        'stats': {},
                        'visibilitySummary': {
                            'attachmentCount': 1,
                            'counts': {'attachment_unparsed': 1},
                            'duplicateSectionTitles': [],
                            'parseWarnings': ['legacy-summary-warning'],
                            'reasonCounts': {'title_detected_without_attachment_body': 1},
                            'manualReviewNeeded': True,
                        },
                    },
                    'visibility': {
                        'attachmentCount': 1,
                        'counts': {'attachment_unparsed': 1},
                        'duplicateSectionTitles': [],
                        'parseWarnings': ['canonical-visibility-warning'],
                        'reasonCounts': {'title_detected_without_attachment_body': 1},
                        'manualReviewNeeded': True,
                        'parserLimited': False,
                        'fileType': 'docx',
                    },
                    'resolvedProfile': {
                        'requestedDocumentType': 'construction_org',
                        'requestedDisciplineTags': ['lifting_operations'],
                        'requestedPolicyPackIds': ['construction_org.base'],
                        'documentType': 'construction_org',
                        'disciplineTags': ['lifting_operations'],
                        'policyPackIds': ['construction_org.base'],
                        'strictMode': True,
                    },
                    'issues': [
                        {
                            'id': 'ISSUE-001',
                            'title': '附件处于可视域缺口，需人工复核原件',
                            'layer': 'L1',
                            'severity': 'medium',
                            'findingType': 'visibility_gap',
                            'summary': '附件处于可视域缺口，需人工复核原件',
                            'manualReviewNeeded': True,
                            'evidenceMissing': True,
                            'manualReviewReason': 'visibility_gap',
                            'docEvidence': [],
                            'policyEvidence': [],
                            'recommendation': [],
                            'confidence': 'medium',
                        }
                    ],
                    'matrices': {
                        'hazardIdentification': {'values': {}},
                        'ruleHits': [],
                        'conflicts': {'values': {}},
                        'attachmentVisibility': [],
                        'sectionStructure': [],
                        'issueLayerCounts': {'L1': 1},
                    },
                    'artifactIndex': [],
                    'reportMarkdown': '# demo',
                    'artifacts': [],
                    'unresolvedFacts': [],
                    'capabilitiesUsed': ['llm_gateway'],
                    'finalAnswer': 'demo',
                },
                createdAt=now,
                updatedAt=now,
            )

        def get_task_events(self, task_id: str):
            return []

        def list_task_artifacts(self, task_id: str):
            return []

    monkeypatch.setattr(tasks_route, 'get_task_service', lambda: FakeService())
    client = TestClient(app)

    result_response = client.get('/api/tasks/task-fresh/result')
    assert result_response.status_code == 200
    result_payload = result_response.json()['result']
    assert result_payload['visibility']['parseWarnings'] == ['canonical-visibility-warning']
    assert 'whetherManualReviewNeeded' not in result_payload['issues'][0]


def test_task_routes_update_reviewer_decision(monkeypatch):
    now = datetime.now(timezone.utc)

    class FakeService:
        def __init__(self):
            self.last_payload = None

        def update_reviewer_decision(self, task_id: str, payload):
            self.last_payload = payload
            return TaskRecord(
                id=task_id,
                taskType='structured_review',
                capabilityMode='auto',
                query='query',
                fixtureId='fixture-1',
                sourceDocumentRef=None,
                sourceUrls=[],
                documentType='construction_org',
                disciplineTags=['lifting_operations'],
                strictMode=True,
                policyPackIds=['construction_org.base'],
                reviewerDecision={
                    'taskState': 'accepted',
                    'note': 'checked',
                    'issues': [
                        {'issueId': 'ISSUE-001', 'state': 'confirmed', 'note': 'ok'},
                    ],
                    'attachments': [
                        {'attachmentId': 'attachment-1', 'state': 'needs_attachment', 'note': 'need original'},
                    ],
                    'updatedAt': now.isoformat(),
                },
                status='succeeded',
                result={
                    'summary': {
                        'overallConclusion': 'demo',
                        'documentType': 'construction_org',
                        'selectedPacks': ['construction_org.base'],
                        'manualReviewNeeded': True,
                        'issueCount': 1,
                        'layerCounts': {'L1': 1},
                        'stats': {},
                        'visibilitySummary': {
                            'attachmentCount': 1,
                            'counts': {'attachment_unparsed': 1},
                            'duplicateSectionTitles': [],
                            'parseWarnings': [],
                            'reasonCounts': {'title_detected_without_attachment_body': 1},
                            'manualReviewNeeded': True,
                        },
                    },
                    'visibility': {
                        'attachmentCount': 1,
                        'counts': {'attachment_unparsed': 1},
                        'duplicateSectionTitles': [],
                        'parseWarnings': [],
                        'reasonCounts': {'title_detected_without_attachment_body': 1},
                        'manualReviewNeeded': True,
                        'parserLimited': False,
                        'fileType': 'docx',
                    },
                    'resolvedProfile': {
                        'requestedDocumentType': 'construction_org',
                        'requestedDisciplineTags': ['lifting_operations'],
                        'requestedPolicyPackIds': [],
                        'documentType': 'construction_org',
                        'disciplineTags': ['lifting_operations'],
                        'policyPackIds': ['construction_org.base'],
                        'strictMode': True,
                    },
                    'issues': [
                        {
                            'id': 'ISSUE-001',
                            'title': '附件处于可视域缺口，需人工复核原件',
                            'layer': 'L1',
                            'severity': 'medium',
                            'findingType': 'visibility_gap',
                            'summary': '附件处于可视域缺口，需人工复核原件',
                            'manualReviewNeeded': True,
                            'evidenceMissing': True,
                            'manualReviewReason': 'visibility_gap',
                            'docEvidence': [],
                            'policyEvidence': [],
                            'recommendation': [],
                            'confidence': 'medium',
                        }
                    ],
                    'matrices': {
                        'hazardIdentification': {'values': {}},
                        'ruleHits': [],
                        'conflicts': {'values': {}},
                        'attachmentVisibility': [
                            {
                                'id': 'attachment-1',
                                'attachmentNumber': '1',
                                'title': '附件1',
                                'visibility': 'attachment_unparsed',
                                'parseState': 'attachment_unparsed',
                                'manualReviewNeeded': True,
                                'reason': 'title_detected_without_attachment_body',
                                'referenceBlockIds': [],
                                'titleBlockId': None,
                            }
                        ],
                        'sectionStructure': [],
                        'issueLayerCounts': {'L1': 1},
                    },
                    'artifactIndex': [],
                    'reportMarkdown': '# demo',
                    'artifacts': [],
                    'unresolvedFacts': [],
                    'capabilitiesUsed': ['llm_gateway'],
                    'finalAnswer': 'demo',
                },
                createdAt=now,
                updatedAt=now,
            )

    fake_service = FakeService()
    monkeypatch.setattr(tasks_route, 'get_task_service', lambda: fake_service)
    client = TestClient(app)

    response = client.put(
        '/api/tasks/task-route-1/reviewer-decision',
        json={
            'taskState': 'accepted',
            'note': 'checked',
            'issues': [{'issueId': 'ISSUE-001', 'state': 'confirmed', 'note': 'ok'}],
            'attachments': [{'attachmentId': 'attachment-1', 'state': 'needs_attachment', 'note': 'need original'}],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert fake_service.last_payload is not None
    assert payload['reviewerDecision']['taskState'] == 'rejected'
    assert payload['reviewerDecision']['issues'][0]['issueId'] == 'ISSUE-001'


def test_task_routes_accept_source_document_ref_without_fixture(monkeypatch):
    now = datetime.now(timezone.utc)

    class FakeService:
        def __init__(self):
            self.last_request = None

        def create_task(self, request):
            self.last_request = request
            return TaskRecord(
                id='task-route-upload-1',
                taskType=request.taskType,
                capabilityMode=request.capabilityMode,
                query=request.query,
                fixtureId=request.fixtureId,
                sourceDocumentRef=request.sourceDocumentRef,
                sourceUrls=[],
                documentType=request.documentType,
                disciplineTags=request.disciplineTags or [],
                strictMode=request.strictMode,
                policyPackIds=request.policyPackIds or [],
                status='created',
                createdAt=now,
                updatedAt=now,
            )

        def schedule_task(self, task_id: str):
            return None

    fake_service = FakeService()
    monkeypatch.setattr(tasks_route, 'get_task_service', lambda: fake_service)
    client = TestClient(app)

    response = client.post(
        '/api/tasks',
        json={
            'taskType': 'structured_review',
            'capabilityMode': 'auto',
            'query': '执行上传文档正式结构化审查',
            'sourceDocumentRef': {
                'refId': 'upload-ref-1',
                'sourceType': 'upload',
                'fileName': 'sample.md',
                'fileType': 'md',
                'storagePath': '/tmp/sample.md',
                'displayName': 'sample.md',
            },
            'documentType': 'construction_org',
            'disciplineTags': ['lifting_operations'],
            'strictMode': True,
            'policyPackIds': ['construction_org.base'],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload['fixtureId'] is None
    assert payload['sourceDocumentRef']['sourceType'] == 'upload'
    assert fake_service.last_request is not None
    assert fake_service.last_request.sourceDocumentRef is not None
    assert fake_service.last_request.fixtureId is None


def test_task_routes_reject_disable_visibility_check_public_field():
    client = TestClient(app)
    response = client.post(
        '/api/tasks',
        json={
            'taskType': 'structured_review',
            'capabilityMode': 'auto',
            'query': '执行正式结构化审查',
            'fixtureId': 'fixture-1',
            'documentType': 'construction_org',
            'disable_visibility_check': True,
        },
    )
    assert response.status_code == 422


def test_support_scope_route_returns_official_and_placeholder_scope():
    client = TestClient(app)
    response = client.get('/api/tasks/support-scope')
    assert response.status_code == 200
    payload = response.json()
    document_types = {item['documentType']: item['readiness'] for item in payload['documentTypes']}
    assert document_types['construction_org'] == 'official'
    assert document_types['hazardous_special_scheme'] == 'official'
    assert document_types['construction_scheme'] == 'experimental'
    assert document_types['supervision_plan'] == 'experimental'
    assert document_types['review_support_material'] == 'experimental'
    packs = {item['packId']: item['readiness'] for item in payload['packs']}
    assert packs['construction_org.base'] == 'ready'
    assert packs['construction_scheme.base'] == 'ready'
    assert packs['supervision_plan.base'] == 'ready'
    assert packs['review_support_material.base'] == 'ready'
    assert packs['gas_area_ops.base'] == 'ready'
    assert any(readiness == 'placeholder' for readiness in packs.values())


def test_upload_route_returns_source_document_ref(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        uploads_route,
        'get_settings',
        lambda: SimpleNamespace(uploads_dir=tmp_path),
    )
    client = TestClient(app)

    response = client.post(
        '/api/uploads/documents',
        files={'file': ('uploaded.md', b'# demo\n\ncontent\n', 'text/markdown')},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload['sourceType'] == 'upload'
    assert payload['fileType'] == 'md'
    stored_path = Path(payload['storagePath'])
    assert stored_path.exists()
    assert stored_path.read_text(encoding='utf-8') == '# demo\n\ncontent\n'


def test_upload_route_rejects_missing_content_type(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        uploads_route,
        'get_settings',
        lambda: SimpleNamespace(uploads_dir=tmp_path),
    )
    client = TestClient(app)

    response = client.post(
        '/api/uploads/documents',
        files={'file': ('uploaded.md', b'# demo\n\ncontent\n', '')},
    )
    assert response.status_code == 400
    assert response.json()['detail'] == 'Missing content type for .md upload'


def test_upload_route_rejects_suffix_mime_mismatch(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        uploads_route,
        'get_settings',
        lambda: SimpleNamespace(uploads_dir=tmp_path),
    )
    client = TestClient(app)

    response = client.post(
        '/api/uploads/documents',
        files={'file': ('uploaded.md', b'# demo\n\ncontent\n', 'application/pdf')},
    )
    assert response.status_code == 400
    assert response.json()['detail'] == 'Unexpected content type for .md upload: application/pdf'


def test_task_routes_list_recent_tasks(monkeypatch):
    now = datetime.now(timezone.utc)

    class FakeService:
        def __init__(self):
            self.last_limit = None

        def list_tasks(self, limit: int = 8):
            self.last_limit = limit
            return [
                TaskRecord(
                    id='task-2',
                    taskType='structured_review',
                    capabilityMode='auto',
                    query='最近任务 2',
                    fixtureId='fixture-b',
                    sourceUrls=[],
                    documentType='hazardous_special_scheme',
                    disciplineTags=[],
                    strictMode=True,
                    policyPackIds=[],
                    status='running',
                    createdAt=now,
                    updatedAt=now,
                ),
                TaskRecord(
                    id='task-1',
                    taskType='knowledge_qa',
                    capabilityMode='fast',
                    query='最近任务 1',
                    fixtureId=None,
                    sourceUrls=[],
                    documentType=None,
                    disciplineTags=[],
                    strictMode=None,
                    policyPackIds=[],
                    status='succeeded',
                    createdAt=now,
                    updatedAt=now,
                ),
            ]

    fake_service = FakeService()
    monkeypatch.setattr(tasks_route, 'get_task_service', lambda: fake_service)
    client = TestClient(app)

    response = client.get('/api/tasks?limit=2')
    assert response.status_code == 200
    payload = response.json()
    assert fake_service.last_limit == 2
    assert [item['id'] for item in payload] == ['task-2', 'task-1']
    assert payload[0]['documentType'] == 'hazardous_special_scheme'
    assert payload[1]['capabilityMode'] == 'fast'


def test_task_stream_returns_snapshot_and_heartbeat(monkeypatch, tmp_path: Path):
    now = datetime.now(timezone.utc)

    class FakeService:
        def __init__(self):
            self.task_call_count = 0

        def get_task(self, task_id: str):
            self.task_call_count += 1
            return TaskRecord(
                id=task_id,
                taskType='structured_review',
                capabilityMode='auto',
                query='stream task',
                fixtureId='fixture-1',
                sourceUrls=[],
                documentType='construction_org',
                disciplineTags=['lifting_operations'],
                strictMode=True,
                policyPackIds=['construction_org.base'],
                status='running' if self.task_call_count == 1 else 'succeeded',
                createdAt=now,
                updatedAt=now,
            )

        def get_task_events(self, task_id: str):
            return []

        def list_task_artifacts(self, task_id: str):
            return [
                TaskArtifact(
                    name='report',
                    fileName='report.json',
                    mediaType='application/json',
                    sizeBytes=12,
                    downloadUrl=f'/api/tasks/{task_id}/artifacts/report.json',
                )
            ]

    fake_service = FakeService()
    monkeypatch.setattr(tasks_route, 'get_task_service', lambda: fake_service)
    monkeypatch.setattr(tasks_route, 'TASK_STREAM_POLL_SECONDS', 0.01)
    monkeypatch.setattr(tasks_route, 'TASK_STREAM_HEARTBEAT_SECONDS', 0.01)
    client = TestClient(app)

    with client.stream('GET', '/api/tasks/task-stream-1/stream') as response:
        assert response.status_code == 200
        chunks: list[str] = []
        for chunk in response.iter_text():
            if not chunk:
                continue
            chunks.append(chunk)
            merged = ''.join(chunks)
            if 'event: snapshot' in merged and 'event: heartbeat' in merged:
                break

    payload = ''.join(chunks)
    assert 'event: snapshot' in payload
    assert 'event: heartbeat' in payload
    assert '"id": "task-stream-1"' in payload
    assert json.dumps('/api/tasks/task-stream-1/artifacts/report.json') in payload
