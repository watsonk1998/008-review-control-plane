from __future__ import annotations

from pathlib import Path

from src.services.document_loader import DocumentLoader
from src.review.pipeline import StructuredReviewExecutor


SAMPLE_DOC = Path(
    '/Users/lucas/repos/review/008-review-control-plane/fixtures/copied/supervision/230235-冷轧厂2030单元三台行车电气系统改造-施工组织设计.docx'
)


class DummyLLM:
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
                'docEvidence': [span.model_dump(mode='json') for span in candidate.docEvidence],
                'policyEvidence': [span.model_dump(mode='json') for span in candidate.policyEvidence],
                'recommendation': ['demo'],
                'confidence': 'medium',
                'whetherManualReviewNeeded': candidate.manualReviewNeeded,
            }
            for index, candidate in enumerate(candidates)
        ]


def test_document_loader_parse_document_extracts_sections_tables_and_attachments():
    loader = DocumentLoader()
    result = loader.parse_document(SAMPLE_DOC)

    assert result.fileType == 'docx'
    assert len(result.sections) > 20
    assert len(result.tables) >= 10
    assert result.visibilityReport['manualReviewNeeded'] is True
    assert '防火安全' in result.visibilityReport['duplicateSectionTitles']
    attachment_map = {item['id']: item for item in result.attachments}
    assert attachment_map['attachment-2']['visibility'] == 'attachment_unparsed'


def test_structured_review_executor_returns_expected_issue_titles():
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=DummyLLM(), fast_adapter=None)
    result = executor.run_sync(
        task_id='structured-review-test',
        query='对该施工组织设计执行正式结构化审查',
        source_document_path=str(SAMPLE_DOC),
        fixture_id='supervision-cold-rolling-construction-plan',
    )

    issue_titles = {issue['title'] for issue in result['issues']}
    assert result['summary']['documentType'] == 'construction_org'
    assert 'construction_org.base' in result['summary']['selectedPacks']
    assert '章节结构存在重复标题，正式审查定位不稳定' in issue_titles
    assert '附件处于可视域缺口，需人工复核原件' in issue_titles
    assert '高风险作业已识别，但专项方案挂接不清' in issue_titles
    assert '停机窗口、投入人力与高风险工序并行存在组织压力' in issue_titles
    assert result['summary']['manualReviewNeeded'] is True
