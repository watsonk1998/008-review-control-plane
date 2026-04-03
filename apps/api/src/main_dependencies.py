from __future__ import annotations

from functools import lru_cache

from src.adapters.deeptutor_adapter import DeepTutorAdapter
from src.adapters.fastgpt_adapter import FastGPTAdapter
from src.adapters.gpt_researcher_adapter import GPTResearcherAdapter
from src.adapters.llm_gateway import LLMGateway
from src.config.settings import get_settings
from src.orchestrator.deepresearch_runtime import DeepResearchRuntime
from src.repositories.sqlite_store import SQLiteTaskStore
from src.services.document_loader import DocumentLoader
from src.services.fixture_service import FixtureService
from src.services.task_service import TaskService


@lru_cache(maxsize=1)
def get_store() -> SQLiteTaskStore:
    return SQLiteTaskStore(get_settings().database_path)


@lru_cache(maxsize=1)
def get_fixture_service() -> FixtureService:
    return FixtureService(get_settings().fixture_manifest_path)


@lru_cache(maxsize=1)
def get_document_loader() -> DocumentLoader:
    return DocumentLoader()


@lru_cache(maxsize=1)
def get_llm_gateway() -> LLMGateway:
    return LLMGateway()


@lru_cache(maxsize=1)
def get_fast_adapter() -> FastGPTAdapter:
    return FastGPTAdapter()


@lru_cache(maxsize=1)
def get_gpt_researcher_adapter() -> GPTResearcherAdapter:
    return GPTResearcherAdapter(get_settings().gpt_researcher_external_path)


@lru_cache(maxsize=1)
def get_deeptutor_adapter() -> DeepTutorAdapter | None:
    base_url = get_settings().deeptutor_base_url
    if not base_url:
        return None
    return DeepTutorAdapter(base_url)


@lru_cache(maxsize=1)
def get_runtime() -> DeepResearchRuntime:
    return DeepResearchRuntime(
        store=get_store(),
        fixture_service=get_fixture_service(),
        document_loader=get_document_loader(),
        llm_gateway=get_llm_gateway(),
        fast_adapter=get_fast_adapter(),
        gpt_researcher=get_gpt_researcher_adapter(),
        deeptutor=get_deeptutor_adapter(),
        tasks_dir=get_settings().tasks_dir,
    )


@lru_cache(maxsize=1)
def get_task_service() -> TaskService:
    return TaskService(get_store(), get_runtime(), get_settings().tasks_dir)


async def get_capability_health():
    results = [
        {'name': 'deepresearch_runtime', 'available': True, 'mode': 'local-compat-runtime', 'detail': 'planner/router/coordinator inside 008 API'},
    ]
    for name, getter in [
        ('llm_gateway', get_llm_gateway),
        ('fastgpt', get_fast_adapter),
        ('gpt_researcher', get_gpt_researcher_adapter),
    ]:
        try:
            result = await getter().health_check()
            result['name'] = name
            results.append(result)
        except Exception as exc:
            results.append({'name': name, 'available': False, 'mode': 'error', 'detail': str(exc)})
    deeptutor = get_deeptutor_adapter()
    if deeptutor is None:
        results.append({'name': 'deeptutor', 'available': False, 'mode': 'not-configured', 'detail': 'DEEPTUTOR_BASE_URL is not set'})
    else:
        try:
            result = await deeptutor.health_check()
            result['name'] = 'deeptutor'
            results.append(result)
        except Exception as exc:
            results.append({'name': 'deeptutor', 'available': False, 'mode': 'error', 'detail': str(exc)})
    return results
