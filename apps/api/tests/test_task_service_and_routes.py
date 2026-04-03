from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.domain.models import CreateTaskRequest, TaskArtifact, TaskRecord
from src.main import app
from src.repositories.sqlite_store import SQLiteTaskStore
from src.routes import tasks as tasks_route
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


def test_task_routes_accept_structured_review_fields_and_serve_artifacts(monkeypatch, tmp_path: Path):
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
                sourceUrls=[],
                documentType='construction_org',
                disciplineTags=['lifting_operations'],
                strictMode=True,
                policyPackIds=['construction_org.base'],
                status='succeeded',
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

    artifacts_response = client.get('/api/tasks/task-route-1/artifacts')
    assert artifacts_response.status_code == 200
    assert artifacts_response.json()[0]['downloadUrl'].endswith('/report.json')

    download_response = client.get('/api/tasks/task-route-1/artifacts/report.json')
    assert download_response.status_code == 200
    assert download_response.text == '{"ok": true}'


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
