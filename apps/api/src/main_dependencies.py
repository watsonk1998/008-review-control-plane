from __future__ import annotations

from functools import lru_cache

from src.adapters.deeptutor_adapter import DeepTutorAdapter
from src.adapters.fastgpt_adapter import FastGPTAdapter
from src.adapters.gpt_researcher_adapter import GPTResearcherAdapter
from src.adapters.hermes_llm_adapter import HermesLLMAdapter
from src.adapters.hermes_external_adapter import HermesExternalAdapter
from src.adapters.hermes_router_adapter import HermesRouterAdapter
from src.adapters.llm_gateway import LLMGateway
from src.config.settings import get_settings
from src.orchestrator.deepresearch_runtime import DeepResearchRuntime
from src.repositories.sqlite_store import SQLiteTaskStore
from src.review.fact_packet_adapter import FactPacketAdapter
from src.review.hermes_controller import HermesController
from src.review.hermes_review_engine import HermesReviewEngine
from src.review.pipeline import StructuredReviewExecutor
from src.review.structured_review_capability_facade import StructuredReviewCapabilityFacade
from src.review.task_compiler import TaskCompiler
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
def get_structured_review_executor() -> StructuredReviewExecutor:
    return StructuredReviewExecutor(
        document_loader=get_document_loader(),
        llm_gateway=get_llm_gateway(),
        fast_adapter=get_fast_adapter(),
    )



@lru_cache(maxsize=1)
def get_structured_review_capability_facade() -> StructuredReviewCapabilityFacade:
    return StructuredReviewCapabilityFacade(
        structured_review_executor=get_structured_review_executor(),
    )

@lru_cache(maxsize=1)
def get_fact_packet_adapter() -> FactPacketAdapter:
    return FactPacketAdapter()


@lru_cache(maxsize=1)
def get_task_compiler() -> TaskCompiler:
    return TaskCompiler()


@lru_cache(maxsize=1)
def get_hermes_controller() -> HermesController:
    repo_root = get_settings().tasks_dir.parent.parent
    return HermesController(
        task_compiler=get_task_compiler(),
        fact_packet_adapter=get_fact_packet_adapter(),
        capability_facade=get_structured_review_capability_facade(),
        hermes_engine=get_hermes_engine(),
        llm_gateway=get_llm_gateway(),
        seed_template_dir=repo_root / 'apps' / 'api' / 'src' / 'review' / 'hermes' / 'templates',
        runtime_template_dir=get_settings().tasks_dir / '_runtime_agent_templates',
    )

@lru_cache(maxsize=1)
def get_hermes_engine() -> HermesReviewEngine:
    endpoint = get_settings().hermes_external_endpoint
    external = HermesExternalAdapter(endpoint=endpoint)
    llm = HermesLLMAdapter(llm_gateway=get_llm_gateway())
    return HermesRouterAdapter(external, llm)


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
        hermes_engine=get_hermes_engine(),
        hermes_controller=get_hermes_controller(),
        tasks_dir=get_settings().tasks_dir,
    )


@lru_cache(maxsize=1)
def get_task_service() -> TaskService:
    return TaskService(get_store(), get_runtime(), get_settings().tasks_dir, get_fixture_service())


async def get_capability_health():
    results = [
        {'name': 'deepresearch_runtime', 'available': True, 'mode': 'local-compat-runtime', 'detail': 'planner/router/coordinator inside 008 API'},
    ]
    for name, getter in [
        ('llm_gateway', get_llm_gateway),
        ('fastgpt', get_fast_adapter),
        ('gpt_researcher', get_gpt_researcher_adapter),
        ('hermes_engine', get_hermes_engine),
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
