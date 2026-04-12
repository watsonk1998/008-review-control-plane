from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from src.domain.governance_schema import AuditLogRecord, DraftRecord, CandidateArtifact


class SQLiteGovernanceStore:
    def __init__(self, database_path: str):
        self.database_path = database_path
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
                CREATE TABLE IF NOT EXISTS governance_drafts (
                    id TEXT PRIMARY KEY,
                    target_entity_type TEXT NOT NULL,
                    target_entity_id TEXT NOT NULL,
                    proposed_changes_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    reviewer_notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS governance_audit_logs (
                    id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    changes_json TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS governance_candidates (
                    id TEXT PRIMARY KEY,
                    profile_id TEXT NOT NULL,
                    candidate_type TEXT NOT NULL,
                    content_text TEXT NOT NULL,
                    source TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    reviewer_notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                '''
            )

    def create_candidate(self, candidate: CandidateArtifact) -> CandidateArtifact:
        with self._connect() as conn:
            conn.execute(
                '''
                INSERT INTO governance_candidates (
                    id, profile_id, candidate_type, content_text,
                    source, status, created_by, reviewer_notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    candidate.id,
                    candidate.profile_id,
                    candidate.candidate_type,
                    candidate.content,
                    candidate.source,
                    candidate.status,
                    candidate.created_by,
                    candidate.reviewer_notes,
                    candidate.created_at.isoformat(),
                    candidate.updated_at.isoformat(),
                ),
            )
        return candidate

    def update_candidate(self, candidate_id: str, **fields: Any) -> CandidateArtifact:
        now = datetime.now(timezone.utc)
        serialized: dict[str, Any] = {'updated_at': now.isoformat()}
        mapping = {
            'status': 'status',
            'reviewer_notes': 'reviewer_notes',
        }
        for key, value in fields.items():
            column = mapping.get(key, key)
            if key in ['status', 'reviewer_notes']:
                serialized[column] = value

        if len(serialized) == 1: # only updated_at
            raise ValueError("No valid fields to update")

        assignments = ', '.join(f"{column} = ?" for column in serialized.keys())
        values = list(serialized.values()) + [candidate_id]
        
        with self._connect() as conn:
            conn.execute(f'UPDATE governance_candidates SET {assignments} WHERE id = ?', values)
            row = conn.execute('SELECT * FROM governance_candidates WHERE id = ?', (candidate_id,)).fetchone()
            
        if not row:
            raise KeyError(f'Candidate not found: {candidate_id}')
        return self._row_to_candidate(row)

    def list_candidates(self, profile_id: str | None = None, status: str | None = None) -> list[CandidateArtifact]:
        with self._connect() as conn:
            query = 'SELECT * FROM governance_candidates'
            params = []
            conditions = []
            if profile_id:
                conditions.append('profile_id = ?')
                params.append(profile_id)
            if status:
                conditions.append('status = ?')
                params.append(status)
            
            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)
            
            query += ' ORDER BY created_at DESC'
            rows = conn.execute(query, tuple(params)).fetchall()
        return [self._row_to_candidate(row) for row in rows]

    def create_draft(self, draft: DraftRecord) -> DraftRecord:
        with self._connect() as conn:
            conn.execute(
                '''
                INSERT INTO governance_drafts (
                    id, target_entity_type, target_entity_id, proposed_changes_json,
                    status, created_by, reviewer_notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    draft.id,
                    draft.target_entity_type,
                    draft.target_entity_id,
                    json.dumps(draft.proposed_changes, ensure_ascii=False),
                    draft.status,
                    draft.created_by,
                    draft.reviewer_notes,
                    draft.created_at.isoformat(),
                    draft.updated_at.isoformat(),
                ),
            )
        return draft

    def update_draft(self, draft_id: str, **fields: Any) -> DraftRecord:
        now = datetime.now(timezone.utc)
        serialized: dict[str, Any] = {'updated_at': now.isoformat()}
        mapping = {
            'target_entity_type': 'target_entity_type',
            'target_entity_id': 'target_entity_id',
            'proposed_changes': 'proposed_changes_json',
            'status': 'status',
            'created_by': 'created_by',
            'reviewer_notes': 'reviewer_notes',
        }
        for key, value in fields.items():
            column = mapping.get(key, key)
            if column == 'proposed_changes_json':
                serialized[column] = json.dumps(value, ensure_ascii=False)
            elif key in ['status', 'target_entity_type', 'target_entity_id', 'created_by', 'reviewer_notes']:
                serialized[column] = value

        if not serialized:
            raise ValueError("No fields to update")

        assignments = ', '.join(f"{column} = ?" for column in serialized.keys())
        values = list(serialized.values()) + [draft_id]
        
        with self._connect() as conn:
            conn.execute(f'UPDATE governance_drafts SET {assignments} WHERE id = ?', values)
            row = conn.execute('SELECT * FROM governance_drafts WHERE id = ?', (draft_id,)).fetchone()
            
        if not row:
            raise KeyError(f'Draft not found: {draft_id}')
        return self._row_to_draft(row)

    def get_draft(self, draft_id: str) -> DraftRecord | None:
        with self._connect() as conn:
            row = conn.execute('SELECT * FROM governance_drafts WHERE id = ?', (draft_id,)).fetchone()
        return self._row_to_draft(row) if row else None

    def list_drafts(self, status: str | None = None) -> list[DraftRecord]:
        with self._connect() as conn:
            if status:
                rows = conn.execute('SELECT * FROM governance_drafts WHERE status = ? ORDER BY created_at DESC', (status,)).fetchall()
            else:
                rows = conn.execute('SELECT * FROM governance_drafts ORDER BY created_at DESC').fetchall()
        return [self._row_to_draft(row) for row in rows]

    def create_audit_log(self, log: AuditLogRecord) -> AuditLogRecord:
        with self._connect() as conn:
            conn.execute(
                '''
                INSERT INTO governance_audit_logs (
                    id, entity_type, entity_id, action, changes_json, created_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    log.id,
                    log.entity_type,
                    log.entity_id,
                    log.action,
                    json.dumps(log.changes, ensure_ascii=False),
                    log.created_by,
                    log.created_at.isoformat(),
                ),
            )
        return log

    def list_audit_logs(self, entity_id: str | None = None) -> list[AuditLogRecord]:
        with self._connect() as conn:
            if entity_id:
                rows = conn.execute('SELECT * FROM governance_audit_logs WHERE entity_id = ? ORDER BY created_at DESC', (entity_id,)).fetchall()
            else:
                rows = conn.execute('SELECT * FROM governance_audit_logs ORDER BY created_at DESC').fetchall()
        return [self._row_to_audit_log(row) for row in rows]

    def _row_to_draft(self, row: sqlite3.Row) -> DraftRecord:
        return DraftRecord(
            id=row['id'],
            target_entity_type=row['target_entity_type'],
            target_entity_id=row['target_entity_id'],
            proposed_changes=json.loads(row['proposed_changes_json']),
            status=row['status'],
            created_by=row['created_by'],
            reviewer_notes=row['reviewer_notes'],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
        )

    def _row_to_audit_log(self, row: sqlite3.Row) -> AuditLogRecord:
        return AuditLogRecord(
            id=row['id'],
            entity_type=row['entity_type'],
            entity_id=row['entity_id'],
            action=row['action'],
            changes=json.loads(row['changes_json']),
            created_by=row['created_by'],
            created_at=datetime.fromisoformat(row['created_at']),
        )

    def _row_to_candidate(self, row: sqlite3.Row) -> CandidateArtifact:
        return CandidateArtifact(
            id=row['id'],
            profile_id=row['profile_id'],
            candidate_type=row['candidate_type'],
            content=row['content_text'],
            source=row['source'],
            status=row['status'],
            created_by=row['created_by'],
            reviewer_notes=row['reviewer_notes'],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
        )
