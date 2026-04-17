from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import sqlite3
from typing import Any

from src.domain.models import (
    AnnotatedFact,
    FactRelationship,
    ReviewerDecision,
    SourceDocumentRef,
    TaskEvent,
    TaskRecord,
)


_TASK_EXTRA_COLUMNS = {
    "document_type": "TEXT",
    "discipline_tags_json": "TEXT",
    "strict_mode": "INTEGER",
    "policy_pack_ids_json": "TEXT",
    "rule_pack_ids_json": "TEXT",
    "source_document_ref_json": "TEXT",
    "reviewer_decision_json": "TEXT",
    "external_context_json": "TEXT",
    "annotated_facts_json": "TEXT",
    "fact_relationships_json": "TEXT",
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
                """
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
                """
            )
            self._ensure_task_columns(conn)
            conn.execute(
                """
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
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS review_report_feedback (
                    id TEXT PRIMARY KEY,
                    report_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    feedback_type TEXT NOT NULL,
                    comment TEXT,
                    source TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

    def _ensure_task_columns(self, conn: sqlite3.Connection):
        rows = conn.execute("PRAGMA table_info(tasks)").fetchall()
        existing = {row["name"] for row in rows}
        for column, column_type in _TASK_EXTRA_COLUMNS.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE tasks ADD COLUMN {column} {column_type}")

    def create_task(self, task: TaskRecord) -> TaskRecord:
        # Generate annotated facts and fact relationships from the task
        annotated_facts = getattr(task, "annotatedFacts", None)
        fact_relationships = getattr(task, "factRelationships", None)

        # If not provided, create them from evidence spans in the task
        if not annotated_facts or not fact_relationships:
            evidence_spans = []
            for field in ["sourceDocumentRef", "policyPackIds", "rulePackIds"]:
                field_value = getattr(task, field, None)
                if isinstance(field_value, list):
                    evidence_spans.extend(field_value)

            annotated_facts = self._create_annotated_facts(
                task.id, evidence_spans, fact_relationships or []
            )
            fact_relationships = self._create_fact_relationships(
                task.id, fact_relationships
            )

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tasks (
                    id, task_type, capability_mode, query, dataset_id, collection_id, fixture_id,
                    source_document_ref_json, use_web, debug, source_urls, document_type, discipline_tags_json, strict_mode,
                    policy_pack_ids_json, rule_pack_ids_json, reviewer_decision_json, external_context_json, status, plan_json, result_json, error_json,
                    annotated_facts_json, fact_relationships_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.id,
                    task.taskType,
                    task.capabilityMode,
                    task.query,
                    task.datasetId,
                    task.collectionId,
                    task.fixtureId,
                    json.dumps(
                        task.sourceDocumentRef.model_dump(mode="json"),
                        ensure_ascii=False,
                    )
                    if task.sourceDocumentRef
                    else None,
                    int(task.useWeb),
                    int(task.debug),
                    json.dumps(task.sourceUrls, ensure_ascii=False),
                    task.documentType,
                    json.dumps(task.disciplineTags, ensure_ascii=False),
                    int(task.strictMode) if task.strictMode is not None else None,
                    json.dumps(task.policyPackIds, ensure_ascii=False),
                    json.dumps(task.rulePackIds, ensure_ascii=False),
                    json.dumps(
                        task.reviewerDecision.model_dump(mode="json"),
                        ensure_ascii=False,
                    )
                    if task.reviewerDecision is not None
                    else None,
                    json.dumps(
                        task.externalContext.model_dump(mode="json"), ensure_ascii=False
                    )
                    if task.externalContext is not None
                    else None,
                    task.status,
                    json.dumps(task.plan, ensure_ascii=False)
                    if task.plan is not None
                    else None,
                    json.dumps(task.result, ensure_ascii=False)
                    if task.result is not None
                    else None,
                    json.dumps(task.error, ensure_ascii=False)
                    if task.error is not None
                    else None,
                    json.dumps(annotated_facts, ensure_ascii=False),
                    json.dumps(fact_relationships, ensure_ascii=False),
                    task.createdAt.isoformat(),
                    task.updatedAt.isoformat(),
                ),
            )
        return task

    def get_task(self, task_id: str) -> TaskRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
        return self._row_to_task(row) if row else None

    def list_tasks(self, limit: int = 8) -> list[TaskRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM tasks ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_task(row) for row in rows]

    def get_task_with_provenance(self, task_id: str) -> TaskRecord | None:
        """Get a task with its annotated facts and fact relationships."""
        task = self.get_task(task_id)
        if not task:
            return None

        # Load annotated facts JSON
        annotated_facts_json = task.annotatedFacts if task.annotatedFacts else "[]"
        task.annotatedFacts = self._load_annotated_facts(annotated_facts_json)

        # Load fact relationships JSON
        fact_relationships_json = (
            task.factRelationships if task.factRelationships else "[]"
        )
        task.factRelationships = self._load_fact_relationships(fact_relationships_json)

        return task

    def count_running_tasks(self) -> int:
        active_statuses = ("created", "planned", "running", "waiting_external")
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM tasks
                WHERE status IN (?, ?, ?, ?)
                """,
                active_statuses,
            ).fetchone()
        return int(row["count"]) if row else 0

    def latest_task_updated_at(self) -> datetime | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT MAX(updated_at) AS updated_at FROM tasks"
            ).fetchone()
        if not row or not row["updated_at"]:
            return None
        return datetime.fromisoformat(row["updated_at"])

    def update_task(self, task_id: str, **fields: Any) -> TaskRecord:
        now = datetime.now(timezone.utc)
        serialized: dict[str, Any] = {"updated_at": now.isoformat()}
        mapping = {
            "taskType": "task_type",
            "capabilityMode": "capability_mode",
            "datasetId": "dataset_id",
            "collectionId": "collection_id",
            "fixtureId": "fixture_id",
            "sourceDocumentRef": "source_document_ref_json",
            "useWeb": "use_web",
            "sourceUrls": "source_urls",
            "documentType": "document_type",
            "disciplineTags": "discipline_tags_json",
            "strictMode": "strict_mode",
            "policyPackIds": "policy_pack_ids_json",
            "rulePackIds": "rule_pack_ids_json",
            "reviewerDecision": "reviewer_decision_json",
            "externalContext": "external_context_json",
            "createdAt": "created_at",
            "updatedAt": "updated_at",
        }
        for key, value in fields.items():
            column = mapping.get(key, key)
            if column in {"plan", "result", "error"}:
                serialized[f"{column}_json"] = (
                    json.dumps(value, ensure_ascii=False) if value is not None else None
                )
            elif column in {
                "source_urls",
                "discipline_tags_json",
                "policy_pack_ids_json",
                "rule_pack_ids_json",
            }:
                serialized[column] = json.dumps(value or [], ensure_ascii=False)
            elif column == "source_document_ref_json":
                serialized[column] = (
                    json.dumps(value.model_dump(mode="json"), ensure_ascii=False)
                    if value is not None
                    else None
                )
            elif column == "reviewer_decision_json":
                serialized[column] = (
                    json.dumps(value.model_dump(mode="json"), ensure_ascii=False)
                    if value is not None
                    else None
                )
            elif column == "external_context_json":
                serialized[column] = (
                    json.dumps(value.model_dump(mode="json"), ensure_ascii=False)
                    if value is not None
                    else None
                )
            elif column in {"use_web", "debug"}:
                serialized[column] = int(bool(value))
            elif column == "strict_mode":
                serialized[column] = int(value) if value is not None else None
            elif column in {"created_at", "updated_at"} and isinstance(value, datetime):
                serialized[column] = value.isoformat()
            else:
                serialized[column] = value

        assignments = ", ".join(f"{column} = ?" for column in serialized.keys())
        values = list(serialized.values()) + [task_id]
        with self._connect() as conn:
            conn.execute(f"UPDATE tasks SET {assignments} WHERE id = ?", values)
            row = conn.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"Task not found: {task_id}")
        return self._row_to_task(row)

    def append_event(self, task_id: str, event: TaskEvent) -> TaskEvent:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO task_events (
                    task_id, timestamp, stage, capability, status, message, duration_ms, debug_json, artifact_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    event.timestamp.isoformat(),
                    event.stage,
                    event.capability,
                    event.status,
                    event.message,
                    event.durationMs,
                    json.dumps(event.debug, ensure_ascii=False)
                    if event.debug is not None
                    else None,
                    event.artifactPath,
                ),
            )
        return event

    def list_events(self, task_id: str) -> list[TaskEvent]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM task_events WHERE task_id = ? ORDER BY id ASC",
                (task_id,),
            ).fetchall()
        return [
            TaskEvent(
                timestamp=datetime.fromisoformat(row["timestamp"]),
                stage=row["stage"],
                capability=row["capability"],
                status=row["status"],
                message=row["message"],
                durationMs=row["duration_ms"],
                debug=json.loads(row["debug_json"]) if row["debug_json"] else None,
                artifactPath=row["artifact_path"],
            )
            for row in rows
        ]

    def append_report_feedback(
        self,
        *,
        feedback_id: str,
        report_id: str,
        task_id: str,
        feedback_type: str,
        comment: str | None,
        source: str | None,
        created_at: datetime,
    ) -> dict[str, Any]:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO review_report_feedback (
                    id, report_id, task_id, feedback_type, comment, source, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    feedback_id,
                    report_id,
                    task_id,
                    feedback_type,
                    comment,
                    source,
                    created_at.isoformat(),
                ),
            )
        return {
            "id": feedback_id,
            "report_id": report_id,
            "task_id": task_id,
            "feedback_type": feedback_type,
            "comment": comment,
            "source": source,
            "created_at": created_at.isoformat(),
        }

    def _generate_entity_id(self, base_id: str, entity_type: str) -> str:
        """Generate a deterministic ID for annotated facts and fact relationships."""
        return hashlib.md5(f"{base_id}_{entity_type}".encode()).hexdigest()[:24]

    def _row_to_task(self, row: sqlite3.Row) -> TaskRecord:
        from src.domain.models import ExternalIntegrationContext

        source_document_ref = self._load_model(
            row["source_document_ref_json"], SourceDocumentRef
        )
        reviewer_decision = self._load_model(
            row["reviewer_decision_json"], ReviewerDecision
        )
        external_context = (
            self._load_model(row["external_context_json"], ExternalIntegrationContext)
            if "external_context_json" in row.keys()
            else None
        )
        annotated_facts = self._load_annotated_facts(
            row["annotated_facts_json"] if "annotated_facts_json" in row.keys() else "[]"
        )
        fact_relationships = self._load_fact_relationships(
            row["fact_relationships_json"] if "fact_relationships_json" in row.keys() else "[]"
        )
        return TaskRecord(
            id=row["id"],
            taskType=row["task_type"],
            capabilityMode=row["capability_mode"],
            query=row["query"],
            datasetId=row["dataset_id"],
            collectionId=row["collection_id"],
            fixtureId=row["fixture_id"],
            sourceDocumentRef=source_document_ref,
            useWeb=bool(row["use_web"]),
            debug=bool(row["debug"]),
            sourceUrls=self._load_list_json(row["source_urls"]),
            documentType=row["document_type"],
            disciplineTags=self._load_list_json(row["discipline_tags_json"]),
            strictMode=bool(row["strict_mode"])
            if row["strict_mode"] is not None
            else None,
            policyPackIds=self._load_list_json(row["policy_pack_ids_json"]),
            rulePackIds=self._load_list_json(row["rule_pack_ids_json"]),
            status=row["status"],
            plan=self._load_json(row["plan_json"]),
            result=self._load_json(row["result_json"]),
            reviewerDecision=reviewer_decision,
            externalContext=external_context,
            error=self._load_json(row["error_json"]),
            annotatedFacts=annotated_facts,
            factRelationships=fact_relationships,
            createdAt=datetime.fromisoformat(row["created_at"]),
            updatedAt=datetime.fromisoformat(row["updated_at"]),
        )

    def _load_json(self, raw: str | None, *, default: Any = None) -> Any:
        if not raw:
            return default
        try:
            return json.loads(raw)
        except Exception:
            return default

    def _load_list_json(self, raw: str | None) -> list[Any]:
        payload = self._load_json(raw, default=[])
        return payload if isinstance(payload, list) else []

    def _load_model(self, raw: str | None, model_cls):
        payload = self._load_json(raw)
        if payload is None:
            return None
        try:
            return model_cls.model_validate(payload)
        except Exception:
            return None

    def _create_annotated_facts(
        self,
        task_id: str,
        evidence_spans: list[EvidenceSpan],
        fact_relationships: list[FactRelationship],
    ) -> list[AnnotatedFact]:
        """Create AnnotatedFact records from evidence spans and relationships."""
        annotated_facts: list[AnnotatedFact] = []
        seen_facts = set()

        # Create annotated facts from evidence spans
        for span in evidence_spans:
            fact_key = f"{span.sourceType}:{span.sourceId}:{span.locator}"
            if fact_key in seen_facts:
                continue
            seen_facts.add(fact_key)

            annotated_facts.append(
                AnnotatedFact(
                    fact_key=fact_key,
                    span_id=span.span_id or "",
                    evidence_span_ids=[span.span_id] if span.span_id else [],
                    provenance_ids=[],
                    value=None,
                    confidence=ConfidenceLevel.medium,
                    is_derived=False,
                    relationship_type="primary",
                )
            )

        # Add relationships as annotated facts
        for rel in fact_relationships:
            annotated_facts.append(
                AnnotatedFact(
                    fact_key=f"relationship:{rel.relationship_id}",
                    span_id=rel.span_id or "",
                    evidence_span_ids=rel.provenance_ids,
                    provenance_ids=rel.provenance_ids,
                    value=None,
                    confidence=ConfidenceLevel.medium,
                    is_derived=True,
                    relationship_type=rel.relationship_type,
                )
            )

        return annotated_facts

    def _create_fact_relationships(
        self, task_id: str, relationships: list[dict] | None
    ) -> list[FactRelationship]:
        """Create FactRelationship records from relationship definitions."""
        if not relationships:
            return []

        fact_relationships: list[FactRelationship] = []
        for rel in relationships:
            fact_relationships.append(
                FactRelationship(
                    relationship_id=rel.get("relationship_id")
                    or self._generate_entity_id(task_id, "relationship"),
                    from_fact_key=rel.get("from_fact_key", ""),
                    to_fact_key=rel.get("to_fact_key", ""),
                    relationship_type=rel.get("relationship_type", "depends_on"),
                    strength=rel.get("strength", 1.0),
                    span_id=rel.get("span_id"),
                    provenance_ids=rel.get("provenance_ids", []),
                )
            )
        return fact_relationships

    def _load_annotated_facts(self, raw: str | None) -> list[AnnotatedFact]:
        payload = self._load_json(raw, default=[])
        if not isinstance(payload, list):
            return []
        facts = []
        for item in payload:
            try:
                facts.append(AnnotatedFact.model_validate(item))
            except Exception:
                continue
        return facts

    def _load_fact_relationships(self, raw: str | None) -> list[FactRelationship]:
        payload = self._load_json(raw, default=[])
        if not isinstance(payload, list):
            return []
        relationships = []
        for item in payload:
            try:
                relationships.append(FactRelationship.model_validate(item))
            except Exception:
                continue
        return relationships
