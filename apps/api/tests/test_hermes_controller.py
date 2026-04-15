from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from src.domain.models import SourceDocumentRef, TaskRecord
from src.review.contracts import FactPacket, FindingItem, ReviewPacketMetrics
from src.review.fact_packet_adapter import FactPacketAdapter
from src.review.hermes_controller import HermesController
from src.review.hermes_review_engine import HermesReviewEngine
from src.review.pipeline import StructuredReviewExecutor
from src.review.structured_review_capability_facade import StructuredReviewCapabilityFacade
from src.review.task_compiler import TaskCompiler
from src.services.document_loader import DocumentLoader


class DummyLLM:
    async def chat(self, messages, temperature=0.2, max_tokens=1200):
        raise RuntimeError('force deterministic candidate fallback')

    def explain_issue_candidates(self, candidates):
        return [
            {
                'id': f'ISSUE-{index + 1:03d}',
                'title': candidate.title,
                'layer': candidate.layerHint,
                'severity': candidate.severityHint,
                'findingType': candidate.findingType,
                'summary': candidate.title,
                'manualReviewNeeded': candidate.manualReviewNeeded,
                'evidenceMissing': candidate.evidenceMissing,
                'manualReviewReason': candidate.manualReviewReason,
                'docEvidence': [span.model_dump(mode='json') for span in candidate.docEvidence],
                'policyEvidence': [span.model_dump(mode='json') for span in candidate.policyEvidence],
                'recommendation': ['demo'],
                'confidence': 'medium',
                'whetherManualReviewNeeded': candidate.manualReviewNeeded,
            }
            for index, candidate in enumerate(candidates)
        ]


class FakeHermesEngine(HermesReviewEngine):
    @property
    def available(self) -> bool:
        return True

    async def health_check(self) -> dict:
        return {'available': True, 'mode': 'fake', 'detail': 'ok'}

    async def review(self, brief, fact_packet_008=None, *, document_preview='') -> FactPacket:
        return FactPacket(
            review_id=brief.review_id,
            engine='hermes',
            findings=[
                FindingItem(
                    id='H-CUSTOM-001',
                    title='停送电执行链路存在遗漏风险',
                    severity='medium',
                    category='consistency',
                    evidence_status='inferred',
                    summary='补充识别到停送电链路的执行衔接风险。',
                    source_engine='hermes',
                )
            ],
            summary_metrics=ReviewPacketMetrics(total_findings=1, medium_severity=1),
            overall_assessment='fake hermes review',
        )


def _write_json_factory(base: Path):
    def _write(name: str, payload):
        path = base / f'{name}.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        import json
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
        return str(path)
    return _write


def _write_text_factory(base: Path):
    def _write(name: str, content: str, suffix: str = '.md'):
        path = base / f'{name}{suffix}'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return str(path)
    return _write


def _write_binary_factory(base: Path):
    def _write(name: str, content: bytes, suffix: str = '.bin'):
        path = base / f'{name}{suffix}'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return str(path)
    return _write


async def test_hermes_controller_selects_agents_generates_candidate_and_reports(tmp_path: Path):
    sample = tmp_path / 'sample.md'
    sample.write_text(
        '# 停电施工方案\n\n## 第一章 工程概况\n停电窗口7天。\n\n## 第二章 施工组织\n涉及施工用电、动火作业。\n\n## 附件1：停电切换图\n',
        encoding='utf-8',
    )
    task = TaskRecord(
        id='task-hermes-001',
        taskType='structured_review',
        capabilityMode='auto',
        query='重点审查停送电控制链路与专项章节完整性',
        datasetId=None,
        collectionId=None,
        fixtureId=None,
        sourceDocumentRef=SourceDocumentRef(
            refId='upload-1',
            sourceType='upload',
            fileName=sample.name,
            fileType='md',
            storagePath=str(sample),
            displayName=sample.name,
        ),
        useWeb=False,
        debug=False,
        sourceUrls=[],
        documentType='distribution_network_special_scheme',
        disciplineTags=['temporary_power'],
        strictMode=True,
        policyPackIds=['power_outage_work.base'],
        status='created',
        plan=None,
        result=None,
        error=None,
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
    )
    llm = DummyLLM()
    controller = HermesController(
        task_compiler=TaskCompiler(),
        fact_packet_adapter=FactPacketAdapter(),
        capability_facade=StructuredReviewCapabilityFacade(
            structured_review_executor=StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=llm, fast_adapter=None),
        ),
        hermes_engine=FakeHermesEngine(),
        llm_gateway=llm,
        basis_pack_resolver=MagicMock(),
        support_packet_builder=MagicMock(),
        seed_template_dir=Path('/Users/lucas/repos/review/008-review-control-plane/apps/api/src/review/hermes/templates'),
        runtime_template_dir=tmp_path / 'runtime_templates',
    )
    with patch('src.review.hermes_controller.render_structured_review_pdf', new=AsyncMock()) as render_pdf:
        result = await controller.run(
            task=task,
            plan={
                'reviewProfile': {
                    'authority': 'test',
                    'documentTypeHint': 'distribution_network_special_scheme',
                    'disciplineTagHints': ['temporary_power'],
                    'policyPackHints': ['power_outage_work.base'],
                },
                'hermesInput': {
                    'basisFiles': [{'path': '/tmp/basis.md', 'type': 'md', 'name': 'basis.md'}],
                    'contextFiles': [],
                    'focusRequirements': ['停送电控制链路', '母线切换校核'],
                    'enabledAgents': ['structured_review_primary_worker', 'execution_risk_reviewer'],
                    'disabledAgents': ['visibility_gap_reviewer'],
                },
            },
            source_document_ref=task.sourceDocumentRef,
            source_document_path=str(sample),
            fixture=None,
            emit=lambda *args, **kwargs: None,
            write_json_artifact=_write_json_factory(tmp_path / 'artifacts'),
            write_text_artifact=_write_text_factory(tmp_path / 'artifacts'),
            write_binary_artifact=_write_binary_factory(tmp_path / 'artifacts'),
        )

    assert result['hermesController']['enabled'] is True
    assert result['hermesController']['mainReviewOwnedBy'] == 'hermes'
    assert result['hermesController']['supportLayerOwnedBy'] == 'structured_review_capability_facade'
    assert 'mainReviewOutcomes' in result['hermesController']
    assert 'selectedAgents' in result['hermesController']
    assert 'finalReportMarkdown' in result
    if 'finalReportPacket' in result:
        assert result['finalReportViewModel']['sections'][0]['title'] == '章节完整性'
        assert result['reportHtml'].startswith('<article class="structured-report structured-report--final">')
        assert result['reportPrintCss']
        assert result['artifactIndex'][0]['artifactRole'] == 'formal_final_report'
        assert result['artifactIndex'][0]['primary'] is True
        assert result['artifactIndex'][0]['fileName'] == 'hermes-controller-final-report.pdf'
        assert result['finalReportPacket']['metadata']['decision_owner'] == 'hermes'
        assert result['finalReportPacket']['metadata']['support_owner'] == 'structured_review_capability_facade'
        assert result['finalReportPacket']['metadata']['selected_review_modules'] == []
    else:
        assert isinstance(result['artifactIndex'], list)

async def test_hermes_controller_handles_degraded_path(tmp_path: Path):
    sample = tmp_path / 'sample.md'
    sample.write_text('# 停电施工方案', encoding='utf-8')
    task = TaskRecord(
        id='task-hermes-degraded',
        taskType='structured_review',
        capabilityMode='auto',
        query='审查',
        datasetId=None,
        collectionId=None,
        fixtureId=None,
        sourceDocumentRef=SourceDocumentRef(
            refId='upload-1',
            sourceType='upload',
            fileName=sample.name,
            fileType='md',
            storagePath=str(sample),
            displayName=sample.name,
        ),
        useWeb=False,
        debug=False,
        sourceUrls=[],
        documentType='distribution_network_special_scheme',
        disciplineTags=[],
        strictMode=True,
        policyPackIds=[],
        status='created',
        plan=None,
        result=None,
        error=None,
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
    )
    llm = DummyLLM()
    # Force the engine to raise an exception
    class FailingEngine(FakeHermesEngine):
        async def review(self, *args, **kwargs):
            raise RuntimeError('Forced failure')
            
    class FailingTemplateRegistry:
        def select_templates(self, *args, **kwargs):
            raise RuntimeError('Forced failure in selection')
            
    controller = HermesController(
        task_compiler=TaskCompiler(),
        fact_packet_adapter=FactPacketAdapter(),
        capability_facade=StructuredReviewCapabilityFacade(
            structured_review_executor=StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=llm, fast_adapter=None),
        ),
        hermes_engine=FailingEngine(),
        llm_gateway=llm,
        basis_pack_resolver=MagicMock(),
        support_packet_builder=MagicMock(),
        seed_template_dir=Path('/Users/lucas/repos/review/008-review-control-plane/apps/api/src/review/hermes/templates'),
        runtime_template_dir=tmp_path / 'runtime_templates',
    )
    controller.template_registry = FailingTemplateRegistry() # to force an exception early
    
    with patch('src.review.hermes_controller.render_structured_review_pdf', new=AsyncMock()) as render_pdf:
        result = await controller.run(
            task=task,
            plan={},
            source_document_ref=task.sourceDocumentRef,
            source_document_path=str(sample),
            fixture=None,
            emit=lambda *args, **kwargs: None,
            write_json_artifact=_write_json_factory(tmp_path / 'artifacts'),
            write_text_artifact=_write_text_factory(tmp_path / 'artifacts'),
            write_binary_artifact=_write_binary_factory(tmp_path / 'artifacts'),
        )

    assert result['hermesController']['enabled'] is False
    assert result['hermesController']['degraded'] is True
    assert 'finalReportMarkdown' in result
    assert 'finalReportPacket' not in result
    assert isinstance(result['artifactIndex'], list)
