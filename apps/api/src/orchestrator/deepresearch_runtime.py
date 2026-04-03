from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

from src.adapters.deeptutor_adapter import DeepTutorAdapter
from src.adapters.fastgpt_adapter import FastGPTAdapter, FastGPTResponseParseError
from src.adapters.gpt_researcher_adapter import GPTResearcherAdapter
from src.adapters.llm_gateway import LLMGateway
from src.domain.models import TaskEvent, TaskRecord
from src.orchestrator.planner import TaskPlanner
from src.orchestrator.router import infer_default_dataset
from src.repositories.sqlite_store import SQLiteTaskStore
from src.review.pipeline import StructuredReviewExecutor
from src.services.document_loader import DocumentLoader
from src.services.fixture_service import FixtureService


class DeepResearchRuntime:
    def __init__(
        self,
        *,
        store: SQLiteTaskStore,
        fixture_service: FixtureService,
        document_loader: DocumentLoader,
        llm_gateway: LLMGateway,
        fast_adapter: FastGPTAdapter,
        gpt_researcher: GPTResearcherAdapter,
        deeptutor: DeepTutorAdapter | None,
        tasks_dir: Path,
    ):
        self.store = store
        self.fixture_service = fixture_service
        self.document_loader = document_loader
        self.llm_gateway = llm_gateway
        self.fast_adapter = fast_adapter
        self.gpt_researcher = gpt_researcher
        self.deeptutor = deeptutor
        self.tasks_dir = tasks_dir
        self.planner = TaskPlanner()
        self.structured_review = StructuredReviewExecutor(
            document_loader=document_loader,
            llm_gateway=llm_gateway,
            fast_adapter=fast_adapter,
        )

    async def execute_task(self, task_id: str):
        task = self.store.get_task(task_id)
        if task is None:
            raise KeyError(f'Task not found: {task_id}')
        fixture = self.fixture_service.get_fixture(task.fixtureId) if task.fixtureId else None
        plan = self.planner.build_plan(task, has_fixture=fixture is not None, fixture_title=fixture.title if fixture else None)
        self.store.update_task(task_id, status='planned', plan=plan)
        self._emit(task_id, 'planning', 'deepresearch_runtime', 'completed', 'Execution plan created', debug=plan)
        self.store.update_task(task_id, status='running')
        self._emit(task_id, 'dispatch', 'deepresearch_runtime', 'started', 'Task execution started')
        try:
            if task.taskType == 'knowledge_qa':
                result = await self._run_knowledge_qa(task, plan)
            elif task.taskType == 'deep_research':
                result = await self._run_deep_research(task, plan)
            elif task.taskType == 'document_research':
                result = await self._run_document_research(task, plan, fixture)
            elif task.taskType == 'review_assist':
                result = await self._run_review_assist(task, plan, fixture)
            elif task.taskType == 'structured_review':
                result = await self._run_structured_review(task, plan, fixture)
            else:
                raise ValueError(f'Unsupported task type: {task.taskType}')
            self.store.update_task(task_id, status='succeeded', result=result)
            self._emit(task_id, 'finalize', 'deepresearch_runtime', 'completed', 'Task completed', debug={'capabilitiesUsed': result.get('capabilitiesUsed')})
        except Exception as exc:
            status = 'partial' if self.store.get_task(task_id) and self.store.get_task(task_id).result else 'failed'
            self.store.update_task(task_id, status=status, error={'message': str(exc)})
            self._emit(task_id, 'finalize', 'deepresearch_runtime', 'failed', str(exc))

    async def _run_knowledge_qa(self, task: TaskRecord, plan: dict) -> dict:
        capabilities = []
        dataset_id = infer_default_dataset(task.query, task.taskType, task.datasetId)
        chunks_result = None
        if task.capabilityMode != 'llm_only':
            chunks_result = await self._retrieve_fast_chunks(task, dataset_id)
            capabilities.append('fast')
        chunks = chunks_result['chunks'] if chunks_result else []
        answer = ''
        artifacts = []
        if chunks_result:
            artifacts.append(self._write_task_artifact(task.id, 'fast-dataset', chunks_result))
        if task.capabilityMode == 'gpt_researcher':
            gptr = await self.gpt_researcher.run_deep_research(task.query, use_web=task.useWeb, source_urls=task.sourceUrls)
            answer = gptr['report']
            capabilities.append('gpt_researcher')
            artifacts.append(self._write_task_artifact(task.id, 'gpt-researcher', gptr))
        elif task.capabilityMode != 'llm_only' and self.deeptutor is not None:
            deeptutor_result = await self.deeptutor.ask_with_context(task.query, chunks)
            answer = deeptutor_result['answer']
            capabilities.append('deeptutor')
            artifacts.append(self._write_task_artifact(task.id, 'deeptutor', deeptutor_result))
        else:
            llm_summary = await self.llm_gateway.summarize_chunks(task.query, chunks)
            answer = llm_summary['content']
            capabilities.append('llm_gateway')
            artifacts.append(self._write_task_artifact(task.id, 'llm-summary', llm_summary))
        return {
            'plan': plan,
            'capabilitiesUsed': capabilities,
            'finalAnswer': answer,
            'sources': self._chunks_to_sources(chunks),
            'steps': [event.model_dump(mode='json') for event in self.store.list_events(task.id)],
            'artifacts': artifacts,
        }

    async def _run_deep_research(self, task: TaskRecord, plan: dict) -> dict:
        gptr = await self.gpt_researcher.run_deep_research(task.query, use_web=task.useWeb, source_urls=task.sourceUrls)
        artifact = self._write_task_artifact(task.id, 'gpt-researcher', gptr)
        self._emit(task.id, 'research', 'gpt_researcher', 'completed', 'Research report generated', artifact_path=artifact)
        summary = await self.llm_gateway.chat([
            {'role': 'system', 'content': 'Summarize research reports into concise Chinese executive summaries.'},
            {'role': 'user', 'content': gptr['report'][:12000]},
        ])
        summary_artifact = self._write_task_artifact(task.id, 'gpt-researcher-summary', summary)
        return {
            'plan': plan,
            'capabilitiesUsed': ['gpt_researcher', 'llm_gateway'],
            'finalAnswer': gptr['report'],
            'summary': summary['content'],
            'sources': gptr.get('sources', []),
            'steps': [event.model_dump(mode='json') for event in self.store.list_events(task.id)],
            'artifacts': [artifact, summary_artifact],
        }

    async def _run_document_research(self, task: TaskRecord, plan: dict, fixture) -> dict:
        if fixture is None:
            raise ValueError('document_research requires a fixtureId')
        doc_path = fixture.copiedPath
        preview = self.document_loader.extract_text(doc_path)[:4000]
        preview_artifact = self._write_task_artifact(task.id, 'document-preview', {'fixture': fixture.model_dump(), 'preview': preview})
        self._emit(task.id, 'document', 'document_loader', 'completed', 'Document parsed', artifact_path=preview_artifact)
        gptr = await self.gpt_researcher.run_local_docs_research(task.query, [doc_path])
        gptr_artifact = self._write_task_artifact(task.id, 'document-research', gptr)
        self._emit(task.id, 'research', 'gpt_researcher', 'completed', 'Local docs research completed', artifact_path=gptr_artifact)
        return {
            'plan': plan,
            'capabilitiesUsed': ['gpt_researcher'],
            'finalAnswer': gptr['report'],
            'sources': gptr.get('sources', []),
            'fixture': fixture.model_dump(),
            'steps': [event.model_dump(mode='json') for event in self.store.list_events(task.id)],
            'artifacts': [preview_artifact, gptr_artifact],
        }

    async def _run_review_assist(self, task: TaskRecord, plan: dict, fixture) -> dict:
        capabilities = []
        dataset_id = infer_default_dataset(task.query, task.taskType, task.datasetId)
        chunks_result = await self._retrieve_fast_chunks(task, dataset_id)
        capabilities.append('fast')
        chunks_artifact = self._write_task_artifact(task.id, 'review-fast', chunks_result)
        chunks = chunks_result['chunks']
        doc_preview = None
        doc_preview_artifact = None
        if fixture is not None:
            doc_preview = self.document_loader.extract_text(fixture.copiedPath)[:4000]
            doc_preview_artifact = self._write_task_artifact(task.id, 'review-doc-preview', {'fixture': fixture.model_dump(), 'preview': doc_preview})
            self._emit(task.id, 'document', 'document_loader', 'completed', 'Review fixture parsed', artifact_path=doc_preview_artifact)
        deep_explanation = None
        if self.deeptutor is not None:
            deep_explanation = await self.deeptutor.ask_with_context(task.query, chunks)
            capabilities.append('deeptutor')
            deep_artifact = self._write_task_artifact(task.id, 'review-deeptutor', deep_explanation)
            self._emit(task.id, 'analysis', 'deeptutor', 'completed', 'DeepTutor explanation ready', artifact_path=deep_artifact)
        gptr = None
        if fixture is not None:
            try:
                gptr = await self.gpt_researcher.run_local_docs_research(task.query, [fixture.copiedPath])
                capabilities.append('gpt_researcher')
                gptr_artifact = self._write_task_artifact(task.id, 'review-gpt-researcher', gptr)
                self._emit(task.id, 'analysis', 'gpt_researcher', 'completed', 'GPT Researcher local report ready', artifact_path=gptr_artifact)
            except Exception as exc:
                self._emit(task.id, 'analysis', 'gpt_researcher', 'failed', f'GPT Researcher unavailable: {exc}')
        synthesis_input = {
            'task': task.model_dump(mode='json'),
            'chunks': chunks[:8],
            'deeptutor': deep_explanation,
            'gptResearcher': gptr,
            'documentPreview': doc_preview,
        }
        summary = await self.llm_gateway.chat([
            {'role': 'system', 'content': '你是审查辅助总控。输出“辅助审查要点”，并明确写出“非正式审查结论”。'},
            {'role': 'user', 'content': json.dumps(synthesis_input, ensure_ascii=False)[:15000]},
        ], max_tokens=1800)
        capabilities.append('llm_gateway')
        summary_artifact = self._write_task_artifact(task.id, 'review-summary', summary)
        artifacts = [chunks_artifact, summary_artifact]
        if doc_preview_artifact:
            artifacts.append(doc_preview_artifact)
        return {
            'plan': plan,
            'capabilitiesUsed': capabilities,
            'finalAnswer': summary['content'],
            'sources': self._chunks_to_sources(chunks),
            'notice': '这是辅助审查结果，不等于正式审查结论。',
            'steps': [event.model_dump(mode='json') for event in self.store.list_events(task.id)],
            'artifacts': artifacts,
        }

    async def _run_structured_review(self, task: TaskRecord, plan: dict, fixture) -> dict:
        if fixture is None:
            raise ValueError('structured_review requires a fixtureId')

        result = await self.structured_review.run(
            task_id=task.id,
            query=task.query,
            source_document_path=fixture.copiedPath,
            fixture_id=fixture.id,
            plan=plan,
            emit=lambda stage, capability, status, message, **kwargs: self._emit(task.id, stage, capability, status, message, **kwargs),
            write_json_artifact=lambda name, payload: self._write_task_artifact(task.id, name, payload),
            write_text_artifact=lambda name, content, suffix='.md': self._write_text_artifact(task.id, name, content, suffix=suffix),
        )
        result['fixture'] = fixture.model_dump()
        result['steps'] = [event.model_dump(mode='json') for event in self.store.list_events(task.id)]
        return result

    async def _retrieve_fast_chunks(self, task: TaskRecord, dataset_id: str | None) -> dict:
        if task.collectionId:
            try:
                result = await self.fast_adapter.search_collection_chunks(task.collectionId, task.query, dataset_id)
                self._emit(task.id, 'retrieval', 'fastgpt', 'completed', 'FastGPT collection retrieval completed')
                return result
            except FastGPTResponseParseError as exc:
                self._emit(task.id, 'retrieval', 'fastgpt', 'failed', f'Mode B parse failed, fallback to mode A: {exc}')
        if not dataset_id:
            raise ValueError('No datasetId available for FastGPT retrieval')
        result = await self.fast_adapter.search_dataset_chunks(dataset_id, task.query)
        self._emit(task.id, 'retrieval', 'fastgpt', 'completed', 'FastGPT dataset retrieval completed')
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

    def _chunks_to_sources(self, chunks: list[dict]) -> list[dict]:
        return [
            {
                'label': chunk.get('sourceLabel'),
                'score': chunk.get('score'),
                'preview': chunk.get('text', '')[:200],
                'mode': chunk.get('mode'),
                'chunkId': chunk.get('chunkId'),
                'datasetId': chunk.get('datasetId'),
            }
            for chunk in chunks[:10]
        ]
