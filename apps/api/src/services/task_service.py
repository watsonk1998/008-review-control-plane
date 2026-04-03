from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import mimetypes
from pathlib import Path
import uuid

from src.domain.models import CreateTaskRequest, TaskArtifact, TaskRecord
from src.orchestrator.deepresearch_runtime import DeepResearchRuntime
from src.repositories.sqlite_store import SQLiteTaskStore


class TaskService:
    def __init__(self, store: SQLiteTaskStore, runtime: DeepResearchRuntime, tasks_dir: Path | None = None):
        self.store = store
        self.runtime = runtime
        self.tasks_dir = tasks_dir or runtime.tasks_dir
        self._running_tasks: dict[str, asyncio.Task] = {}

    def create_task(self, request: CreateTaskRequest) -> TaskRecord:
        now = datetime.now(timezone.utc)
        strict_mode = request.strictMode
        if request.taskType == 'structured_review' and strict_mode is None:
            strict_mode = True
        task = TaskRecord(
            id=uuid.uuid4().hex,
            taskType=request.taskType,
            capabilityMode=request.capabilityMode,
            query=request.query,
            datasetId=request.datasetId,
            collectionId=request.collectionId,
            fixtureId=request.fixtureId,
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

    def list_task_artifacts(self, task_id: str) -> list[TaskArtifact]:
        task = self.store.get_task(task_id)
        if task is None:
            raise KeyError(f'Task not found: {task_id}')
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
