from __future__ import annotations

from pathlib import Path

from src.services.document_loader import DocumentLoader
from src.review.pipeline import StructuredReviewExecutor


SAMPLE_DOC = Path(
    '/Users/lucas/repos/review/008-review-control-plane/fixtures/supervision/施工组织设计-冷轧厂2030单元三台行车电气系统改造.docx'
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


def test_document_loader_parse_document_extracts_sections_tables_and_attachments():
    loader = DocumentLoader()
    result = loader.parse_document(SAMPLE_DOC)

    assert result.fileType == 'docx'
    assert len(result.sections) > 20
    assert len(result.tables) >= 10
    assert result.visibilityReport['manualReviewNeeded'] is True
    assert '防火安全' in result.visibilityReport['duplicateSectionTitles']
    assert result.visibilityReport['reasonCounts']['title_detected_without_attachment_body'] >= 1
    attachment_map = {item['id']: item for item in result.attachments}
    assert attachment_map['attachment-2']['visibility'] == 'attachment_unparsed'
    assert attachment_map['attachment-2']['manualReviewNeeded'] is True
    assert attachment_map['attachment-2']['reason'] == 'title_detected_without_attachment_body'


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
    assert result['summary']['visibilitySummary']['attachmentCount'] >= 1
    assert result['summary']['visibilitySummary']['counts']['attachment_unparsed'] >= 1
    assert isinstance(result['unresolvedFacts'], list)
    attachment_issue = next(issue for issue in result['issues'] if issue['title'] == '附件处于可视域缺口，需人工复核原件')
    assert attachment_issue['manualReviewNeeded'] is True
    assert attachment_issue['manualReviewReason'] == 'visibility_gap'
    assert 'whetherManualReviewNeeded' in attachment_issue
    assert 'evidenceMissing' in attachment_issue


def test_structured_review_executor_supports_hazardous_special_scheme(tmp_path: Path):
    sample = tmp_path / 'hazardous_special_scheme.md'
    sample.write_text(
        '# 危大专项施工方案\n\n'
        '## 工程概况\n项目名称：危大专项测试\n'
        '## 编制依据\n依据专项审查要求编制。\n'
        '起重吊装作业。\n'
        '附件1：吊装平面图\n',
        encoding='utf-8',
    )
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=DummyLLM(), fast_adapter=None)
    result = executor.run_sync(
        task_id='hazardous-review-test',
        query='对该危大专项方案执行正式结构化审查',
        source_document_path=str(sample),
        fixture_id='hazardous-review-fixture',
        document_type='hazardous_special_scheme',
        discipline_tags=['lifting_operations'],
    )

    issue_titles = {issue['title'] for issue in result['issues']}
    assert result['summary']['documentType'] == 'hazardous_special_scheme'
    assert 'hazardous_special_scheme.base' in result['resolvedProfile']['policyPackIds']
    assert '危大专项方案核心章节不完整' in issue_titles
    assert '专项方案附件处于可视域缺口，需人工复核原件' in issue_titles
    assert '专项方案缺少可追溯验算依据' in issue_titles
    assert result['summary']['visibilitySummary']['manualReviewNeeded'] is True
