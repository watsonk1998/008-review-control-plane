from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import importlib
import os
import sys
import tempfile
from typing import Any

from src.config.llm import resolve_embedding_config, resolve_llm_config
from src.services.document_loader import DocumentLoader


class GPTResearcherAdapter:
    def __init__(self, external_path: str | None = None):
        self.external_path = external_path or os.getenv('GPT_RESEARCHER_EXTERNAL_PATH')
        self.document_loader = DocumentLoader()

    def _configure_environment(self):
        llm_config = resolve_llm_config()
        embedding_config = resolve_embedding_config()
        fast_model = os.getenv('GPT_RESEARCHER_FAST_MODEL') or llm_config.model
        smart_model = os.getenv('GPT_RESEARCHER_SMART_MODEL') or llm_config.model
        strategic_model = os.getenv('GPT_RESEARCHER_STRATEGIC_MODEL') or llm_config.model

        os.environ.setdefault('OPENAI_API_KEY', llm_config.api_key)
        os.environ.setdefault('OPENAI_BASE_URL', llm_config.base_url)
        os.environ.setdefault('FAST_LLM', f'openai:{fast_model}')
        os.environ.setdefault('SMART_LLM', f'openai:{smart_model}')
        os.environ.setdefault('STRATEGIC_LLM', f'openai:{strategic_model}')
        os.environ.setdefault('EMBEDDING', f'openai:{embedding_config.model}')
        os.environ.setdefault('OPENAI_EMBEDDING_MODEL', embedding_config.model)
        os.environ.setdefault('RETRIEVER', os.getenv('GPT_RESEARCHER_RETRIEVER', 'duckduckgo'))
        os.environ.setdefault('REPORT_FORMAT', 'markdown')
        os.environ.setdefault('LANGUAGE', 'chinese')
        os.environ.setdefault('MAX_SEARCH_RESULTS_PER_QUERY', os.getenv('GPT_RESEARCHER_MAX_SEARCH_RESULTS', '5'))
        os.environ.setdefault('MAX_ITERATIONS', os.getenv('GPT_RESEARCHER_MAX_ITERATIONS', '2'))
        os.environ.setdefault('TEMPERATURE', os.getenv('GPT_RESEARCHER_TEMPERATURE', '0.2'))
        return {
            'llm': llm_config.sanitized(),
            'embedding': embedding_config.sanitized(),
            'retriever': os.environ.get('RETRIEVER'),
            'maxIterations': os.environ.get('MAX_ITERATIONS'),
        }

    def _prepare_import(self):
        self._configure_environment()
        if 'ddgs' not in sys.modules:
            try:
                sys.modules['ddgs'] = importlib.import_module('duckduckgo_search')
            except Exception:
                pass
        if self.external_path:
            repo_path = str(Path(self.external_path).expanduser())
            if repo_path not in sys.path:
                sys.path.insert(0, repo_path)
        module = importlib.import_module('gpt_researcher')
        enum_module = importlib.import_module('gpt_researcher.utils.enum')
        costs_module = importlib.import_module('gpt_researcher.utils.costs')
        llm_utils_module = importlib.import_module('gpt_researcher.utils.llm')
        compression_module = importlib.import_module('gpt_researcher.context.compression')

        original_estimate = costs_module.estimate_llm_cost
        original_embedding_estimate = costs_module.estimate_embedding_cost

        def safe_estimate_llm_cost(input_content: str, output_content: str) -> float:
            try:
                return original_estimate(input_content, output_content)
            except Exception:
                return 0.0

        def safe_estimate_embedding_cost(model: str, docs: list) -> float:
            try:
                return original_embedding_estimate(model, docs)
            except Exception:
                return 0.0

        costs_module.estimate_llm_cost = safe_estimate_llm_cost
        costs_module.estimate_embedding_cost = safe_estimate_embedding_cost
        llm_utils_module.estimate_llm_cost = safe_estimate_llm_cost
        compression_module.estimate_embedding_cost = safe_estimate_embedding_cost
        return module.GPTResearcher, enum_module.ReportType, enum_module.ReportSource, enum_module.Tone

    async def health_check(self) -> dict[str, Any]:
        try:
            env = self._configure_environment()
            self._prepare_import()
            return {
                'available': True,
                'mode': 'python-package',
                'detail': self.external_path or 'import from environment',
                'env': env,
            }
        except Exception as exc:
            return {'available': False, 'mode': 'python-package', 'detail': str(exc)}

    @contextmanager
    def _doc_path_context(self, document_paths: list[str]):
        with tempfile.TemporaryDirectory(prefix='gptr-docs-') as tmp_dir:
            temp_root = Path(tmp_dir)
            for path in document_paths:
                source = Path(path)
                target = temp_root / source.name
                try:
                    target.symlink_to(source)
                except OSError:
                    target.write_bytes(source.read_bytes())
            old_doc_path = os.getenv('DOC_PATH')
            os.environ['DOC_PATH'] = str(temp_root)
            try:
                yield str(temp_root)
            finally:
                if old_doc_path is None:
                    os.environ.pop('DOC_PATH', None)
                else:
                    os.environ['DOC_PATH'] = old_doc_path

    def _build_langchain_documents(self, document_paths: list[str]):
        document_module = importlib.import_module('langchain_core.documents')
        document_class = document_module.Document
        documents = []
        for path in document_paths:
            text = self.document_loader.extract_text(path)
            documents.append(
                document_class(
                    page_content=text,
                    metadata={
                        'title': Path(path).name,
                        'source': Path(path).name,
                        'path': str(path),
                    },
                )
            )
        return documents

    def _build_document_context(self, document_paths: list[str]) -> tuple[str, list[dict[str, str]]]:
        context_parts: list[str] = []
        sources: list[dict[str, str]] = []
        for path in document_paths:
            text = self.document_loader.extract_text(path)
            trimmed = text[:24000]
            context_parts.append(f"文档：{Path(path).name}\n\n{trimmed}")
            sources.append(
                {
                    'type': 'local_document',
                    'title': Path(path).name,
                    'path': str(path),
                    'preview': trimmed[:600],
                }
            )
        return '\n\n---\n\n'.join(context_parts), sources

    async def run_deep_research(self, query: str, *, use_web: bool, source_urls: list[str] | None = None) -> dict[str, Any]:
        GPTResearcher, ReportType, ReportSource, Tone = self._prepare_import()
        researcher = GPTResearcher(
            query=query,
            report_type=ReportType.DeepResearch.value,
            report_source=ReportSource.Web.value if use_web or source_urls else ReportSource.Static.value,
            source_urls=source_urls,
            tone=Tone.Analytical,
            verbose=False,
        )
        await researcher.conduct_research()
        report = await researcher.write_report()
        return {
            'report': report,
            'sources': researcher.get_research_sources(),
            'meta': {
                'reportType': ReportType.DeepResearch.value,
                'reportSource': ReportSource.Web.value if use_web or source_urls else ReportSource.Static.value,
                'sourceUrlCount': len(source_urls or []),
            },
        }

    async def run_local_docs_research(self, query: str, document_paths: list[str]) -> dict[str, Any]:
        GPTResearcher, ReportType, ReportSource, Tone = self._prepare_import()
        ext_context, sources = self._build_document_context(document_paths)
        researcher = GPTResearcher(
            query=query,
            report_type=ReportType.ResearchReport.value,
            report_source=ReportSource.Static.value,
            tone=Tone.Analytical,
            agent='document_researcher',
            role='你是一名建筑工程文档研究分析师。请严格依据给定文档上下文生成报告，不要杜撰未提供的事实。',
            verbose=False,
        )
        report = await researcher.write_report(ext_context=ext_context)
        return {
            'report': report,
            'sources': sources,
            'meta': {
                'reportType': ReportType.ResearchReport.value,
                'reportSource': 'static_context_from_local_docs',
                'documentCount': len(document_paths),
                'documentPaths': document_paths,
            },
        }
