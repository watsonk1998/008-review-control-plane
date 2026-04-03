from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import sqlite3
from typing import Any

from src.domain.models import SourceDocumentRef, TaskEvent, TaskRecord


_TASK_EXTRA_COLUMNS = {
    'document_type': 'TEXT',
    'discipline_tags_json': 'TEXT',
    'strict_mode': 'INTEGER',
    'policy_pack_ids_json': 'TEXT',
    'source_document_ref_json': 'TEXT',
    'reviewer_decision_json': 'TEXT',
}


class SQLiteTaskStore:
    def __init__(self, database_path):
        self.database_path = str(database_path)
        self._init_db()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self):
        with self._connect() as conn:
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,
                    capability_mode TEXT NOT NULL,
                    query TEXT NOT NULL,
                    dataset_id TEXT,
                    collection_id TEXT,
                    fixture_id TEXT,
                    use_web INTEGER NOT NULL,
                    debug INTEGER NOT NULL,
                    source_urls TEXT NOT NULL,
                    status TEXT NOT NULL,
                    plan_json TEXT,
                    result_json TEXT,
                    error_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                '''
            )
            self._ensure_task_columns(conn)
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS task_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    capability TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT NOT NULL,
                    duration_ms INTEGER,
                    debug_json TEXT,
                    artifact_path TEXT
                )
                '''
            )

    def _ensure_task_columns(self, conn: sqlite3.Connection):
        rows = conn.execute('PRAGMA table_info(tasks)').fetchall()
        existing = {row['name'] for row in rows}
        for column, column_type in _TASK_EXTRA_COLUMNS.items():
            if column not in existing:
                conn.execute(f'ALTER TABLE tasks ADD COLUMN {column} {column_type}')

    def create_task(self, task: TaskRecord) -> TaskRecord:
        with self._connect() as conn:
            conn.execute(
                '''
                INSERT INTO tasks (
                    id, task_type, capability_mode, query, dataset_id, collection_id, fixture_id,
                    source_document_ref_json, use_web, debug, source_urls, document_type, discipline_tags_json, strict_mode,
                    policy_pack_ids_json, reviewer_decision_json, status, plan_json, result_json, error_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    task.id,
                    task.taskType,
                    task.capabilityMode,
                    task.query,
                    task.datasetId,
                    task.collectionId,
                    task.fixtureId,
                    json.dumps(task.sourceDocumentRef.model_dump(mode='json'), ensure_ascii=False) if task.sourceDocumentRef else None,
                    int(task.useWeb),
                    int(task.debug),
                    json.dumps(task.sourceUrls, ensure_ascii=False),
                    task.documentType,
                    json.dumps(task.disciplineTags, ensure_ascii=False),
                    int(task.strictMode) if task.strictMode is not None else None,
                    json.dumps(task.policyPackIds, ensure_ascii=False),
                    json.dumps(task.reviewerDecision.model_dump(mode='json'), ensure_ascii=False) if task.reviewerDecision is not None else None,
                    task.status,
                    json.dumps(task.plan, ensure_ascii=False) if task.plan is not None else None,
                    json.dumps(task.result, ensure_ascii=False) if task.result is not None else None,
                    json.dumps(task.error, ensure_ascii=False) if task.error is not None else None,
                    task.createdAt.isoformat(),
                    task.updatedAt.isoformat(),
                ),
            )
        return task

    def get_task(self, task_id: str) -> TaskRecord | None:
        with self._connect() as conn:
            row = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
        return self._row_to_task(row) if row else None

    def list_tasks(self, limit: int = 8) -> list[TaskRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                'SELECT * FROM tasks ORDER BY updated_at DESC LIMIT ?',
                (limit,),
            ).fetchall()
        return [self._row_to_task(row) for row in rows]

    def count_running_tasks(self) -> int:
        active_statuses = ('created', 'planned', 'running', 'waiting_external')
        with self._connect() as conn:
            row = conn.execute(
                '''
                SELECT COUNT(*) AS count
                FROM tasks
                WHERE status IN (?, ?, ?, ?)
                ''',
                active_statuses,
            ).fetchone()
        return int(row['count']) if row else 0

    def latest_task_updated_at(self) -> datetime | None:
        with self._connect() as conn:
            row = conn.execute('SELECT MAX(updated_at) AS updated_at FROM tasks').fetchone()
        if not row or not row['updated_at']:
            return None
        return datetime.fromisoformat(row['updated_at'])

    def update_task(self, task_id: str, **fields: Any) -> TaskRecord:
        now = datetime.now(timezone.utc)
        serialized: dict[str, Any] = {'updated_at': now.isoformat()}
        mapping = {
            'taskType': 'task_type',
            'capabilityMode': 'capability_mode',
            'datasetId': 'dataset_id',
            'collectionId': 'collection_id',
            'fixtureId': 'fixture_id',
            'sourceDocumentRef': 'source_document_ref_json',
            'useWeb': 'use_web',
            'sourceUrls': 'source_urls',
            'documentType': 'document_type',
            'disciplineTags': 'discipline_tags_json',
            'strictMode': 'strict_mode',
            'policyPackIds': 'policy_pack_ids_json',
            'reviewerDecision': 'reviewer_decision_json',
            'createdAt': 'created_at',
            'updatedAt': 'updated_at',
        }
        for key, value in fields.items():
            column = mapping.get(key, key)
            if column in {'plan', 'result', 'error'}:
                serialized[f'{column}_json'] = json.dumps(value, ensure_ascii=False) if value is not None else None
            elif column in {'source_urls', 'discipline_tags_json', 'policy_pack_ids_json'}:
                serialized[column] = json.dumps(value or [], ensure_ascii=False)
            elif column == 'source_document_ref_json':
                serialized[column] = json.dumps(value.model_dump(mode='json'), ensure_ascii=False) if value is not None else None
            elif column == 'reviewer_decision_json':
                serialized[column] = json.dumps(value.model_dump(mode='json'), ensure_ascii=False) if value is not None else None
            elif column in {'use_web', 'debug'}:
                serialized[column] = int(bool(value))
            elif column == 'strict_mode':
                serialized[column] = int(value) if value is not None else None
            elif column in {'created_at', 'updated_at'} and isinstance(value, datetime):
                serialized[column] = value.isoformat()
            else:
                serialized[column] = value

        assignments = ', '.join(f"{column} = ?" for column in serialized.keys())
        values = list(serialized.values()) + [task_id]
        with self._connect() as conn:
            conn.execute(f'UPDATE tasks SET {assignments} WHERE id = ?', values)
            row = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
        if row is None:
            raise KeyError(f'Task not found: {task_id}')
        return self._row_to_task(row)

    def append_event(self, task_id: str, event: TaskEvent) -> TaskEvent:
        with self._connect() as conn:
            conn.execute(
                '''
                INSERT INTO task_events (
                    task_id, timestamp, stage, capability, status, message, duration_ms, debug_json, artifact_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    task_id,
                    event.timestamp.isoformat(),
                    event.stage,
                    event.capability,
                    event.status,
                    event.message,
                    event.durationMs,
                    json.dumps(event.debug, ensure_ascii=False) if event.debug is not None else None,
                    event.artifactPath,
                ),
            )
        return event

    def list_events(self, task_id: str) -> list[TaskEvent]:
        with self._connect() as conn:
            rows = conn.execute('SELECT * FROM task_events WHERE task_id = ? ORDER BY id ASC', (task_id,)).fetchall()
        return [
            TaskEvent(
                timestamp=datetime.fromisoformat(row['timestamp']),
                stage=row['stage'],
                capability=row['capability'],
                status=row['status'],
                message=row['message'],
                durationMs=row['duration_ms'],
                debug=json.loads(row['debug_json']) if row['debug_json'] else None,
                artifactPath=row['artifact_path'],
            )
            for row in rows
        ]

    def _row_to_task(self, row: sqlite3.Row) -> TaskRecord:
        return TaskRecord(
            id=row['id'],
            taskType=row['task_type'],
            capabilityMode=row['capability_mode'],
            query=row['query'],
            datasetId=row['dataset_id'],
            collectionId=row['collection_id'],
            fixtureId=row['fixture_id'],
            sourceDocumentRef=SourceDocumentRef.model_validate(json.loads(row['source_document_ref_json'])) if row['source_document_ref_json'] else None,
            useWeb=bool(row['use_web']),
            debug=bool(row['debug']),
            sourceUrls=json.loads(row['source_urls']) if row['source_urls'] else [],
            documentType=row['document_type'],
            disciplineTags=json.loads(row['discipline_tags_json']) if row['discipline_tags_json'] else [],
            strictMode=bool(row['strict_mode']) if row['strict_mode'] is not None else None,
            policyPackIds=json.loads(row['policy_pack_ids_json']) if row['policy_pack_ids_json'] else [],
            status=row['status'],
            plan=json.loads(row['plan_json']) if row['plan_json'] else None,
            result=json.loads(row['result_json']) if row['result_json'] else None,
            reviewerDecision=json.loads(row['reviewer_decision_json']) if row['reviewer_decision_json'] else None,
            error=json.loads(row['error_json']) if row['error_json'] else None,
            createdAt=datetime.fromisoformat(row['created_at']),
            updatedAt=datetime.fromisoformat(row['updated_at']),
        )
