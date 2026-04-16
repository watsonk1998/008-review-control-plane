from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json

from src.adapters.llm_gateway import LLMGateway
from src.domain.models import SourceDocumentRef, TaskEvent, TaskRecord
from src.orchestrator.router import choose_structured_review_profile
from src.repositories.sqlite_store import SQLiteTaskStore
from src.review.hermes_review_engine import HermesReviewEngine
from src.review.hermes_controller import HermesController
from src.services.document_loader import DocumentLoader
from src.services.fixture_service import FixtureService


class ReviewRuntime:
    def __init__(
        self,
        *,
        store: SQLiteTaskStore,
        fixture_service: FixtureService,
        document_loader: DocumentLoader,
        llm_gateway: LLMGateway,
        hermes_engine: HermesReviewEngine,
        hermes_controller: HermesController,
        tasks_dir: Path,
    ):
        self.store = store
        self.fixture_service = fixture_service
        self.document_loader = document_loader
        self.llm_gateway = llm_gateway
        self.tasks_dir = tasks_dir
        self.hermes_engine = hermes_engine
        self.hermes_controller = hermes_controller

    async def execute_task(self, task_id: str):
        task = self.store.get_task(task_id)
        if task is None:
            raise KeyError(f'Task not found: {task_id}')
        fixture = self.fixture_service.get_fixture(task.fixtureId) if task.fixtureId else None
        plan = self._build_plan(task, fixture)
        if task.plan:
            plan = self._merge_plan_seed(plan, task.plan)
        self.store.update_task(task_id, status='planned', plan=plan)
        self._emit(task_id, 'planning', 'runtime', 'completed', 'Execution plan created', debug=plan)
        self.store.update_task(task_id, status='running')
        self._emit(task_id, 'dispatch', 'runtime', 'started', 'Task execution started')
        try:
            if task.taskType == 'structured_review':
                result = await self._run_structured_review(task, plan, fixture)
            else:
                raise ValueError(f'Unsupported task type: {task.taskType}')
            self.store.update_task(task_id, status='succeeded', result=result)
            self._emit(task_id, 'finalize', 'runtime', 'completed', 'Task completed', debug={'capabilitiesUsed': result.get('capabilitiesUsed')})

            updated_task = self.store.get_task(task_id)
            if updated_task and updated_task.externalContext:
                from src.services.external_callbacks import trigger_task_status_callback
                await trigger_task_status_callback(task_id, 'succeeded', updated_task.externalContext)

        except Exception as exc:
            status = 'partial' if self.store.get_task(task_id) and self.store.get_task(task_id).result else 'failed'
            self.store.update_task(task_id, status=status, error={'message': str(exc)})
            self._emit(task_id, 'finalize', 'runtime', 'failed', str(exc))

            updated_task = self.store.get_task(task_id)
            if updated_task and updated_task.externalContext:
                from src.services.external_callbacks import trigger_task_status_callback
                await trigger_task_status_callback(task_id, status, updated_task.externalContext)

    def _build_plan(self, task: TaskRecord, fixture=None) -> dict:
        review_profile = choose_structured_review_profile(
            task.query,
            fixture.title if fixture else None,
            requested_document_type=task.documentType,
            requested_discipline_tags=task.disciplineTags,
            requested_policy_pack_ids=task.policyPackIds,
            requested_rule_pack_ids=task.rulePackIds,
            strict_mode=task.strictMode,
        )
        return {
            'goal': 'Execute formal structured review through the review domain pipeline',
            'taskType': task.taskType,
            'reviewProfile': review_profile,
            'execution': [
                {'stage': 'plan', 'owner': 'runtime'},
                {'stage': 'parse', 'owner': 'review_parser'},
                {'stage': 'extract', 'owner': 'review_extractors'},
                {'stage': 'rules', 'owner': 'review_rule_engine'},
                {'stage': 'evidence', 'owner': 'review_evidence_builder'},
                {'stage': 'explain', 'owner': 'llm_gateway'},
                {'stage': 'report', 'owner': 'review_report_builder'},
                {'stage': 'finalize', 'owner': 'runtime'},
            ],
        }

    async def _run_structured_review(self, task: TaskRecord, plan: dict, fixture) -> dict:
        source_document_ref, source_document_path, resolved_fixture = self._resolve_source_document(task, fixture)
        if source_document_ref is None or source_document_path is None:
            raise ValueError('structured_review requires a fixtureId or sourceDocumentRef')

        emit_fn = lambda stage, capability, status, message, **kwargs: self._emit(task.id, stage, capability, status, message, **kwargs)
        write_json_fn = lambda name, payload: self._write_task_artifact(task.id, name, payload)

        plan = self._with_default_hermes_input(task=task, plan=plan, source_document_path=source_document_path)

        result = await self.hermes_controller.run(
            task=task,
            plan=plan,
            source_document_ref=source_document_ref,
            source_document_path=source_document_path,
            fixture=resolved_fixture,
            emit=emit_fn,
            write_json_artifact=write_json_fn,
            write_text_artifact=lambda name, content, suffix='.md': self._write_text_artifact(task.id, name, content, suffix=suffix),
            write_binary_artifact=lambda name, content, suffix='.bin': self._write_binary_artifact(task.id, name, content, suffix=suffix),
        )

        if resolved_fixture is not None:
            result['fixture'] = resolved_fixture.model_dump()
        result['steps'] = [event.model_dump(mode='json') for event in self.store.list_events(task.id)]
        return result

    def _emit(self, task_id: str, stage: str, capability: str, status: str, message: str, *, duration_ms: int | None = None, debug: dict | None = None, artifact_path: str | None = None):
        event = TaskEvent(
            timestamp=datetime.now(timezone.utc),
            stage=stage,
            capability=capability,
            status=status,
            message=message,
            durationMs=duration_ms,
            debug=debug,
            artifactPath=artifact_path,
        )
        self.store.append_event(task_id, event)

    def _write_task_artifact(self, task_id: str, name: str, payload) -> str:
        task_dir = self.tasks_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        path = task_dir / f'{name}.json'
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return str(path)

    def _write_text_artifact(self, task_id: str, name: str, content: str, *, suffix: str = '.md') -> str:
        task_dir = self.tasks_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        safe_suffix = suffix if suffix.startswith('.') else f'.{suffix}'
        path = task_dir / f'{name}{safe_suffix}'
        path.write_text(content, encoding='utf-8')
        return str(path)

    def _write_binary_artifact(self, task_id: str, name: str, content: bytes, *, suffix: str = '.bin') -> str:
        task_dir = self.tasks_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        safe_suffix = suffix if suffix.startswith('.') else f'.{suffix}'
        path = task_dir / f'{name}{safe_suffix}'
        path.write_bytes(content)
        return str(path)

    def _resolve_source_document(self, task: TaskRecord, fixture) -> tuple[SourceDocumentRef | None, str | None, object | None]:
        if task.sourceDocumentRef is not None:
            return task.sourceDocumentRef, task.sourceDocumentRef.storagePath, fixture
        if fixture is not None:
            return (
                SourceDocumentRef(
                    refId=fixture.id,
                    sourceType='fixture',
                    fileName=Path(fixture.copiedPath).name,
                    fileType=fixture.fileType,
                    storagePath=fixture.copiedPath,
                    displayName=fixture.title,
                    fixtureId=fixture.id,
                ),
                fixture.copiedPath,
                fixture,
            )
        if task.fixtureId:
            resolved_fixture = self.fixture_service.get_fixture(task.fixtureId)
            if resolved_fixture is not None:
                return (
                    SourceDocumentRef(
                        refId=resolved_fixture.id,
                        sourceType='fixture',
                        fileName=Path(resolved_fixture.copiedPath).name,
                        fileType=resolved_fixture.fileType,
                        storagePath=resolved_fixture.copiedPath,
                        displayName=resolved_fixture.title,
                        fixtureId=resolved_fixture.id,
                    ),
                    resolved_fixture.copiedPath,
                    resolved_fixture,
                )
        return None, None, fixture

    def _merge_plan_seed(self, generated_plan: dict, seeded_plan: dict) -> dict:
        merged = dict(generated_plan)
        for key, value in (seeded_plan or {}).items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = {**merged[key], **value}
            else:
                merged[key] = value
        return merged

    def _with_default_hermes_input(self, *, task: TaskRecord, plan: dict, source_document_path: str) -> dict:
        enriched = dict(plan or {})
        if enriched.get('hermesInput'):
            return enriched
        repo_root = Path(__file__).resolve().parents[4]
        basis_files: list[dict[str, Any]] = []
        candidate_basis = [
            repo_root / 'fixtures/construction/《危险性较大的分部分项工程专项施工方案编制指南》（建办质〔2021〕48号）.md',
            repo_root / 'fixtures/construction/《建设工程施工现场消防安全技术规范》GB 50720-2011.md',
        ]
        if '停电' in task.query or '配网' in task.query or '停电' in Path(source_document_path).name:
            candidate_basis.insert(0, repo_root / 'fixtures/construction/《建设工程安全生产管理条例》.md')
        for path in candidate_basis:
            if path.exists():
                basis_files.append({'path': str(path), 'type': path.suffix.lstrip('.'), 'name': path.name})
        focus_parts = [task.query]
        if '停电' in task.query or '停电' in Path(source_document_path).name:
            focus_parts.append('重点看停送电控制链路')
        focus_parts.append('专项章节完整性')
        focus_parts.append('弱化格式性问题')
        enriched['hermesInput'] = {
            'basisFiles': basis_files[:2],
            'contextFiles': [],
            'focusRequirements': focus_parts,
            'enabledAgents': [],
            'disabledAgents': [],
        }
        return enriched
