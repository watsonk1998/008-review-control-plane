from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import uuid

from src.domain.models import CreateTaskRequest, TaskRecord
from src.orchestrator.deepresearch_runtime import DeepResearchRuntime
from src.repositories.sqlite_store import SQLiteTaskStore


class TaskService:
    def __init__(self, store: SQLiteTaskStore, runtime: DeepResearchRuntime):
        self.store = store
        self.runtime = runtime
        self._running_tasks: dict[str, asyncio.Task] = {}

    def create_task(self, request: CreateTaskRequest) -> TaskRecord:
        now = datetime.now(timezone.utc)
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

    def get_task_events(self, task_id: str):
        return self.store.list_events(task_id)

    def get_task_result(self, task_id: str):
        task = self.store.get_task(task_id)
        if task is None:
            return None
        return task.result
