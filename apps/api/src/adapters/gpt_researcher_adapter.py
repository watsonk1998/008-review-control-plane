from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import importlib
import os
import sys
import tempfile
from typing import Any


class GPTResearcherAdapter:
    def __init__(self, external_path: str | None = None):
        self.external_path = external_path or os.getenv('GPT_RESEARCHER_EXTERNAL_PATH')

    def _prepare_import(self):
        if self.external_path:
            repo_path = str(Path(self.external_path).expanduser())
            if repo_path not in sys.path:
                sys.path.insert(0, repo_path)
        module = importlib.import_module('gpt_researcher')
        enum_module = importlib.import_module('gpt_researcher.utils.enum')
        return module.GPTResearcher, enum_module.ReportType, enum_module.ReportSource, enum_module.Tone

    async def health_check(self) -> dict[str, Any]:
        try:
            self._prepare_import()
            return {'available': True, 'mode': 'python-package', 'detail': self.external_path or 'import from environment'}
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
        with self._doc_path_context(document_paths) as doc_path:
            researcher = GPTResearcher(
                query=query,
                report_type=ReportType.DetailedReport.value,
                report_source=ReportSource.Local.value,
                tone=Tone.Analytical,
                verbose=False,
            )
            await researcher.conduct_research()
            report = await researcher.write_report()
        return {
            'report': report,
            'sources': researcher.get_research_sources(),
            'meta': {
                'reportType': ReportType.DetailedReport.value,
                'reportSource': ReportSource.Local.value,
                'documentCount': len(document_paths),
                'docPath': doc_path,
            },
        }
