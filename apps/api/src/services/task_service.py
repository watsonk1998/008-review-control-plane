from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import mimetypes
from pathlib import Path
import uuid

from src.domain.models import CreateTaskRequest, ReviewerDecisionUpdateRequest, SourceDocumentRef, TaskArtifact, TaskRecord
from src.orchestrator.deepresearch_runtime import DeepResearchRuntime
from src.repositories.sqlite_store import SQLiteTaskStore
from src.review.reviewer_decision import merge_reviewer_decision


class TaskService:
    def __init__(self, store: SQLiteTaskStore, runtime: DeepResearchRuntime, tasks_dir: Path | None = None, fixture_service=None):
        self.store = store
        self.runtime = runtime
        self.tasks_dir = tasks_dir or runtime.tasks_dir
        self.fixture_service = fixture_service
        self._running_tasks: dict[str, asyncio.Task] = {}

    def create_task(self, request: CreateTaskRequest) -> TaskRecord:
        now = datetime.now(timezone.utc)
        strict_mode = request.strictMode
        if request.taskType == 'structured_review' and strict_mode is None:
            strict_mode = True
        source_document_ref = request.sourceDocumentRef
        if request.taskType == 'structured_review' and source_document_ref is None and request.fixtureId and self.fixture_service is not None:
            fixture = self.fixture_service.get_fixture(request.fixtureId)
            if fixture is not None:
                source_document_ref = SourceDocumentRef(
                    refId=fixture.id,
                    sourceType='fixture',
                    fileName=Path(fixture.copiedPath).name,
                    fileType=fixture.fileType,
                    storagePath=fixture.copiedPath,
                    displayName=fixture.title,
                    fixtureId=fixture.id,
                    mediaType=mimetypes.guess_type(fixture.copiedPath)[0],
                )
        task = TaskRecord(
            id=uuid.uuid4().hex,
            taskType=request.taskType,
            capabilityMode=request.capabilityMode,
            query=request.query,
            datasetId=request.datasetId,
            collectionId=request.collectionId,
            fixtureId=request.fixtureId,
            sourceDocumentRef=source_document_ref,
            useWeb=request.useWeb,
            debug=request.debug,
            sourceUrls=request.sourceUrls or [],
            documentType=request.documentType,
            disciplineTags=request.disciplineTags or [],
            strictMode=strict_mode,
            policyPackIds=request.policyPackIds or [],
            status='created',
            createdAt=now,
            updatedAt=now,
        )
        self.store.create_task(task)
        return task

    def schedule_task(self, task_id: str):
        self._running_tasks[task_id] = asyncio.create_task(self.runtime.execute_task(task_id))

    def get_task(self, task_id: str):
        return self.store.get_task(task_id)

    def list_tasks(self, limit: int = 8):
        return self.store.list_tasks(limit=limit)

    def get_task_events(self, task_id: str):
        return self.store.list_events(task_id)

    def get_task_result(self, task_id: str):
        task = self.store.get_task(task_id)
        if task is None:
            return None
        return task.result

    def update_reviewer_decision(self, task_id: str, payload: ReviewerDecisionUpdateRequest) -> TaskRecord:
        task = self.store.get_task(task_id)
        if task is None:
            raise KeyError(f'Task not found: {task_id}')
        if task.taskType != 'structured_review':
            raise ValueError('reviewer decision is only supported for structured_review tasks')
        decision = merge_reviewer_decision(task, payload)
        return self.store.update_task(task_id, reviewerDecision=decision)

    def list_task_artifacts(self, task_id: str) -> list[TaskArtifact]:
        task = self.store.get_task(task_id)
        if task is None:
            raise KeyError(f'Task not found: {task_id}')
        artifact_index = ((task.result or {}).get('artifactIndex') if isinstance(task.result, dict) else None) or []
        catalog = [self._coerce_artifact(item) for item in artifact_index]
        catalog = [item for item in catalog if item is not None]
        if catalog:
            return catalog
        task_dir = self.tasks_dir / task_id
        if not task_dir.exists():
            return []
        artifacts: list[TaskArtifact] = []
        for path in sorted(task_dir.iterdir()):
            if not path.is_file():
                continue
            media_type, _ = mimetypes.guess_type(path.name)
            artifacts.append(
                TaskArtifact(
                    name=path.stem,
                    fileName=path.name,
                    mediaType=media_type or 'application/octet-stream',
                    sizeBytes=path.stat().st_size,
                    downloadUrl=f'/api/tasks/{task_id}/artifacts/{path.name}',
                    category=self._infer_artifact_category(path.name),
                    stage='generated',
                    primary=path.suffix == '.md',
                )
            )
        return artifacts

    def resolve_task_artifact(self, task_id: str, artifact_name: str) -> Path:
        task = self.store.get_task(task_id)
        if task is None:
            raise KeyError(f'Task not found: {task_id}')
        safe_name = Path(artifact_name).name
        path = (self.tasks_dir / task_id / safe_name).resolve()
        task_dir = (self.tasks_dir / task_id).resolve()
        if not str(path).startswith(str(task_dir)):
            raise FileNotFoundError(artifact_name)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(artifact_name)
        return path

    def _coerce_artifact(self, item) -> TaskArtifact | None:
        if not isinstance(item, dict):
            return None
        return TaskArtifact.model_validate(item)

    def _infer_artifact_category(self, file_name: str) -> str:
        if 'parse' in file_name:
            return 'parse'
        if 'fact' in file_name:
            return 'facts'
        if 'rule' in file_name:
            return 'rule_hits'
        if 'candidate' in file_name:
            return 'candidates'
        if 'matrix' in file_name:
            return 'matrix'
        if file_name.endswith('.md'):
            return 'report'
        if 'result' in file_name:
            return 'result'
        return 'generic'
