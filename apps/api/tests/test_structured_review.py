from __future__ import annotations

import asyncio
import json
from pathlib import Path

from src.services.document_loader import DocumentLoader
from src.review.parser.attachment_indexer import build_attachment_index
from src.review.pipeline import StructuredReviewExecutor


REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_DOC = REPO_ROOT / 'fixtures' / 'supervision' / '施工组织设计-冷轧厂2030单元三台行车电气系统改造.docx'
SAMPLE_PDF = REPO_ROOT / 'fixtures' / 'review_eval' / 'hazardous_special_scheme' / 'ci' / 'cn_hz_pdf_unknown_visibility_ci' / 'v0.1.0-ci-stage-gate' / 'source.pdf'
SAMPLE_PUHUA_PDF = REPO_ROOT / 'fixtures' / 'supervision' / '施工组织设计-培花初期雨水调蓄池建设工程.pdf'


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
    assert result.parseMode == 'docx_structured'
    assert result.parserLimited is False
    assert result.visibility.parseMode == 'docx_structured'
    assert len(result.sections) > 20
    assert len(result.tables) >= 10
    assert result.visibility.manualReviewNeeded is True
    assert result.visibility.manualReviewReason == 'title_detected_without_attachment_body'
    assert result.visibilityReport['manualReviewNeeded'] is True
    assert result.visibilityReport['manualReviewReason'] == 'title_detected_without_attachment_body'
    assert '防火安全' in result.visibilityReport['duplicateSectionTitles']
    assert result.visibilityReport['reasonCounts']['title_detected_without_attachment_body'] >= 1
    attachment_map = {item.id: item for item in result.attachments}
    assert attachment_map['attachment-2'].visibility == 'attachment_unparsed'
    assert attachment_map['attachment-2'].manualReviewNeeded is True
    assert attachment_map['attachment-2'].reason == 'title_detected_without_attachment_body'


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
    assert result['visibility']['manualReviewNeeded'] is True
    assert result['visibility']['parseMode'] == 'docx_structured'
    assert result['visibility']['manualReviewReason'] == 'title_detected_without_attachment_body'
    assert '- parse mode：docx_structured' in result['reportMarkdown']
    assert '- manual review reason：title_detected_without_attachment_body' in result['reportMarkdown']
    assert result['visibility']['parseWarnings'] == result['summary']['visibilitySummary']['parseWarnings']
    assert result['summary']['visibilitySummary']['attachmentCount'] >= 1
    assert result['summary']['visibilitySummary']['counts']['attachment_unparsed'] >= 1
    assert isinstance(result['unresolvedFacts'], list)
    attachment_issue = next(issue for issue in result['issues'] if issue['title'] == '附件处于可视域缺口，需人工复核原件')
    assert attachment_issue['manualReviewNeeded'] is True
    assert attachment_issue['manualReviewReason'] == 'visibility_gap'
    assert attachment_issue['issueKind'] == 'visibility_gap'
    assert attachment_issue['applicabilityState'] == 'blocked_by_visibility'
    assert 'whetherManualReviewNeeded' not in attachment_issue
    assert 'evidenceMissing' in attachment_issue
    assert all('packReadiness' in row for row in result['matrices']['ruleHits'])


def test_structured_review_executor_supports_construction_scheme_base_and_ready_scenario_pack(tmp_path: Path):
    sample = tmp_path / 'construction_scheme.md'
    sample.write_text(
        '# 施工方案\n\n'
        '## 工程概况\n项目名称：一般施工方案测试\n项目编号：CS-DEMO\n'
        '起重吊装作业。\n'
        '附件1：吊装平面图\n',
        encoding='utf-8',
    )
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=DummyLLM(), fast_adapter=None)
    result = executor.run_sync(
        task_id='construction-scheme-review-test',
        query='对该施工方案执行正式结构化审查',
        source_document_path=str(sample),
        fixture_id='construction-scheme-review-fixture',
        document_type='construction_scheme',
        discipline_tags=['lifting_operations'],
    )

    issue_titles = {issue['title'] for issue in result['issues']}
    assert result['summary']['documentType'] == 'construction_scheme'
    assert result['resolvedProfile']['policyPackIds'] == ['construction_scheme.base', 'lifting_operations.base']
    assert '一般施工方案核心章节不完整' in issue_titles
    assert '施工方案附件处于可视域缺口，需人工复核原件' in issue_titles
    assert '起重吊装关键参数或验算依据不可追溯' in issue_titles


def test_structured_review_executor_supports_supervision_plan_base_pack(tmp_path: Path):
    sample = tmp_path / 'supervision_plan.md'
    sample.write_text(
        '# 监理规划\n\n'
        '## 工程概况\n项目名称：监理规划测试\n项目编号：SP-DEMO\n'
        '## 编制依据\n依据监理规范编制。\n',
        encoding='utf-8',
    )
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=DummyLLM(), fast_adapter=None)
    result = executor.run_sync(
        task_id='supervision-plan-review-test',
        query='对该监理规划执行正式结构化审查',
        source_document_path=str(sample),
        fixture_id='supervision-plan-review-fixture',
        document_type='supervision_plan',
    )

    issue_titles = {issue['title'] for issue in result['issues']}
    assert result['summary']['documentType'] == 'supervision_plan'
    assert result['resolvedProfile']['policyPackIds'] == ['supervision_plan.base']
    assert '监理规划核心章节不完整' in issue_titles
    assert '监理规划缺少明确的监测监控/旁站安排' in issue_titles


def test_structured_review_executor_supports_review_support_material_base_pack(tmp_path: Path):
    sample = tmp_path / 'review_support_material.md'
    sample.write_text(
        '# 审查支持材料\n\n'
        '材料说明：用于补充背景，不形成正式方案。\n',
        encoding='utf-8',
    )
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=DummyLLM(), fast_adapter=None)
    result = executor.run_sync(
        task_id='review-support-material-test',
        query='对该审查支持材料执行正式结构化审查',
        source_document_path=str(sample),
        fixture_id='review-support-material-fixture',
        document_type='review_support_material',
    )

    issue_titles = {issue['title'] for issue in result['issues']}
    assert result['summary']['documentType'] == 'review_support_material'
    assert result['resolvedProfile']['policyPackIds'] == ['review_support_material.base']
    assert issue_titles == {'审查支持材料不能替代正式方案正文'}


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


def test_document_loader_parse_pdf_document_uses_explicit_pdf_parser():
    loader = DocumentLoader()
    result = loader.parse_document(SAMPLE_PDF)

    assert result.fileType == 'pdf'
    assert result.parseMode == 'pdf_text_only'
    assert result.parserLimited is True
    assert result.visibility.parseMode == 'pdf_text_only'
    assert result.visibility.parserLimited is True
    assert result.visibility.manualReviewNeeded is True
    assert result.visibility.manualReviewReason == 'title_detected_but_body_not_reliably_parsed'
    assert result.visibility.preflight.gateDecision == 'manual_review_required'
    assert 'parser_limited_pdf' in result.visibility.preflight.blockingReasons
    assert result.visibility.counts['unknown'] >= 1
    assert result.visibility.counts['missing'] == 0
    assert result.attachments[0].visibility == 'unknown'
    assert result.attachments[0].reason == 'title_detected_but_body_not_reliably_parsed'
    assert any(warning.startswith('pdf_appendix_title_candidates:') for warning in result.parseWarnings)
    assert any(warning.startswith('pdf_table_caption_candidates:') for warning in result.parseWarnings)
    assert any(warning.startswith('pdf_figure_caption_candidates:') for warning in result.parseWarnings)
    assert any(warning.startswith('pdf_source_pages:') for warning in result.parseWarnings)
    assert any(warning.startswith('pdf_extracted_pages:') for warning in result.parseWarnings)


def test_structured_review_executor_frontloads_manual_review_for_parser_limited_pdf():
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=DummyLLM(), fast_adapter=None)
    result = executor.run_sync(
        task_id='construction-org-puhua-review-test',
        query='对该施工组织设计执行正式结构化审查',
        source_document_path=str(SAMPLE_PUHUA_PDF),
        fixture_id='puhua-review-fixture',
        document_type='construction_org',
        discipline_tags=['lifting_operations', 'temporary_power', 'hot_work'],
    )

    assert result['visibility']['parseMode'] == 'pdf_text_only'
    assert result['visibility']['parserLimited'] is True
    assert result['visibility']['manualReviewNeeded'] is True
    assert result['visibility']['manualReviewReason'] == 'parser_limited_pdf_requires_manual_review'
    assert result['visibility']['preflight']['gateDecision'] == 'manual_review_required'
    assert 'parser_limited_pdf' in result['visibility']['preflight']['blockingReasons']
    assert result['summary']['manualReviewNeeded'] is True
    assert any(
        issue['applicabilityState'] == 'blocked_by_missing_fact' and issue['missingFactKeys']
        for issue in result['issues']
    )
    assert any(
        row['ruleId'] == 'construction_org_emergency_plan_targeted'
        and row['clauseIds']
        and row['blockingReasons']
        and row['applicabilityState'] == 'blocked_by_missing_fact'
        for row in result['matrices']['ruleHits']
    )
    assert any(
        fact['factKey'] == 'emergency.planTitles'
        and fact['sourceExtractor'] == 'schedule_resource_facts'
        and fact['blockingRuleIds']
        for fact in result['unresolvedFacts']
    )


def test_attachment_index_freezes_parser_limited_unknown_and_missing_boundaries():
    title_only_blocks = [{'id': 'b1', 'text': '附件1：吊装平面图'}]
    attachments, _ = build_attachment_index(title_only_blocks, parser_limited=True, file_type='pdf')
    assert attachments[0]['visibility'] == 'unknown'
    assert attachments[0]['reason'] == 'title_detected_but_body_not_reliably_parsed'

    reference_only_blocks = [{'id': 'b2', 'text': '详见附件2。'}]
    attachments, _ = build_attachment_index(reference_only_blocks, parser_limited=True, file_type='pdf')
    assert attachments[0]['visibility'] == 'unknown'
    assert attachments[0]['reason'] == 'reference_detected_in_limited_parser'

    non_limited_title_only = [{'id': 'b3', 'text': '附件3：应急平面布置图'}]
    attachments, _ = build_attachment_index(non_limited_title_only, parser_limited=False, file_type='docx')
    assert attachments[0]['visibility'] == 'attachment_unparsed'
    assert attachments[0]['reason'] == 'title_detected_without_attachment_body'

    explicit_missing_blocks = [{'id': 'b4', 'text': '附件4：吊装验算书（后补，暂缺）'}]
    attachments, _ = build_attachment_index(explicit_missing_blocks, parser_limited=False, file_type='docx')
    assert attachments[0]['visibility'] == 'missing'
    assert attachments[0]['reason'] == 'explicit_missing_marker'


def test_structured_review_rule_hits_expose_applicability_state_and_keep_visibility_gap_out_of_hard_defect():
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=DummyLLM(), fast_adapter=None)
    result = executor.run_sync(
        task_id='structured-review-visibility-applicability-test',
        query='对该施工组织设计执行正式结构化审查',
        source_document_path=str(SAMPLE_DOC),
        fixture_id='supervision-cold-rolling-construction-plan',
    )

    attachment_row = next(row for row in result['matrices']['ruleHits'] if row['ruleId'] == 'construction_org_attachment_visibility')
    assert attachment_row['applicabilityState'] == 'blocked_by_visibility'
    attachment_issue = next(issue for issue in result['issues'] if issue['title'] == '附件处于可视域缺口，需人工复核原件')
    assert attachment_issue['issueKind'] == 'visibility_gap'
    assert attachment_issue['applicabilityState'] == 'blocked_by_visibility'


def test_structured_review_visible_scope_negative_facts_stay_hard_defects():
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=DummyLLM(), fast_adapter=None)
    result = executor.run_sync(
        task_id='structured-review-negative-fact-closure',
        query='对该施工组织设计执行正式结构化审查',
        source_document_path=str(SAMPLE_DOC),
        fixture_id='supervision-cold-rolling-construction-plan',
    )

    structure_row = next(row for row in result['matrices']['ruleHits'] if row['ruleId'] == 'construction_org_structure_completeness')
    structure_issue = next(issue for issue in result['issues'] if issue['title'] == '施工组织设计核心章节不完整')
    assert structure_row['applicabilityState'] == 'applies'
    assert structure_row['missingFactKeys'] == []
    assert structure_row['blockingReasons'] == []
    assert structure_issue['issueKind'] == 'hard_defect'
    assert structure_issue['applicabilityState'] == 'applies'
    assert structure_issue['evidenceMissing'] is False
    assert structure_issue['missingFactKeys'] == []
    assert structure_issue['blockingReasons'] == []


def test_structured_review_parser_limited_negative_facts_stay_blocked_with_explainability():
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=DummyLLM(), fast_adapter=None)
    result = executor.run_sync(
        task_id='structured-review-parser-limited-negative-facts',
        query='对该危大专项方案执行正式结构化审查',
        source_document_path=str(SAMPLE_PDF),
        fixture_id='cn_hz_pdf_unknown_visibility_ci',
        document_type='hazardous_special_scheme',
        discipline_tags=['lifting_operations'],
    )

    core_row = next(row for row in result['matrices']['ruleHits'] if row['ruleId'] == 'hazardous_special_scheme_core_sections')
    core_issue = next(issue for issue in result['issues'] if issue['title'] == '危大专项方案核心章节不完整')
    unresolved_fact = next(
        fact for fact in result['unresolvedFacts'] if fact['factKey'] == 'project.sectionPresence.engineeringOverview'
    )
    assert core_row['applicabilityState'] == 'blocked_by_missing_fact'
    assert core_row['missingFactKeys']
    assert 'missing_fact' in core_row['blockingReasons']
    assert 'parser_limited_source' in core_row['blockingReasons']
    assert core_issue['issueKind'] == 'evidence_gap'
    assert core_issue['applicabilityState'] == 'blocked_by_missing_fact'
    assert core_issue['evidenceMissing'] is True
    assert core_issue['missingFactKeys']
    assert 'parser_limited_source' in core_issue['blockingReasons']
    assert unresolved_fact['visibilityLimited'] is True
    assert 'hazardous_special_scheme_core_sections' in unresolved_fact['blockingRuleIds']
    assert core_issue['id'] in unresolved_fact['blockingIssueIds']


def test_structured_review_executor_supports_gas_area_ops_pack(tmp_path: Path):
    sample = tmp_path / 'construction_org_gas_area.md'
    sample.write_text(
        '# 施工组织设计\n\n'
        '## 工程概况\n项目名称：煤气区域改造项目\n项目编号：GAS-DEMO\n'
        '煤气区域作业安排如下。\n'
        '## 安全技术措施\n仅提供概括性措施。\n',
        encoding='utf-8',
    )
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=DummyLLM(), fast_adapter=None)
    result = executor.run_sync(
        task_id='gas-area-review-test',
        query='对该施工组织设计执行正式结构化审查',
        source_document_path=str(sample),
        fixture_id='gas-area-review-fixture',
        document_type='construction_org',
        discipline_tags=['gas_area_ops'],
    )

    issue_titles = {issue['title'] for issue in result['issues']}
    assert 'gas_area_ops.base' in result['resolvedProfile']['policyPackIds']
    assert '煤气区域作业控制与应急链路不完整' in issue_titles


def test_structured_review_executor_ignores_visibility_ablation_without_internal_flag():
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=DummyLLM(), fast_adapter=None)
    result = executor.run_sync(
        task_id='structured-review-no-visibility-ablation',
        query='对该施工组织设计执行正式结构化审查',
        source_document_path=str(SAMPLE_DOC),
        fixture_id='supervision-cold-rolling-construction-plan',
        execution_options={'disable_visibility_check': True},
    )

    assert result['visibility']['manualReviewNeeded'] is True
    assert result['summary']['visibilitySummary']['counts']['attachment_unparsed'] >= 1
    assert 'disable_visibility_check' not in result['visibility']['parseWarnings']


def test_structured_review_executor_builds_full_artifact_catalog(tmp_path: Path):
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=DummyLLM(), fast_adapter=None)

    def write_json_artifact(name: str, payload):
        path = tmp_path / f'{name}.json'
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        return str(path)

    def write_text_artifact(name: str, content: str, suffix: str):
        path = tmp_path / f'{name}{suffix}'
        path.write_text(content, encoding='utf-8')
        return str(path)

    result = asyncio.run(
        executor.run(
            task_id='structured-review-artifacts',
            query='对该施工组织设计执行正式结构化审查',
            source_document_path=str(SAMPLE_DOC),
            fixture_id='supervision-cold-rolling-construction-plan',
            write_json_artifact=write_json_artifact,
            write_text_artifact=write_text_artifact,
        )
    )

    artifact_categories = {artifact['category'] for artifact in result['artifactIndex']}
    assert {'parse', 'facts', 'rule_hits', 'candidates', 'result', 'matrices', 'report'}.issubset(artifact_categories)
    artifact_names = {artifact['name'] for artifact in result['artifactIndex']}
    assert 'structured-review-l0-visibility' in artifact_names
    assert 'structured-review-report-buckets' in artifact_names
    l0_payload = json.loads((tmp_path / 'structured-review-l0-visibility.json').read_text(encoding='utf-8'))
    assert l0_payload['parseMode'] == 'docx_structured'
    assert l0_payload['parserLimited'] is False
    assert l0_payload['manualReviewNeeded'] is True
    assert l0_payload['manualReviewReason'] == 'title_detected_without_attachment_body'
    assert l0_payload['visibility']['parseMode'] == 'docx_structured'
    assert l0_payload['visibility']['manualReviewReason'] == 'title_detected_without_attachment_body'
    assert l0_payload['preflight']['gateDecision'] == 'manual_review_required'
    result_payload = json.loads((tmp_path / 'structured-review-result.json').read_text(encoding='utf-8'))
    assert result_payload['artifactIndex']
    assert result_payload['reportMarkdown']
    assert result_payload['visibility'] == l0_payload['visibility']
    assert result_payload['visibility']['preflight']['gateDecision'] == 'manual_review_required'
    report_buckets = json.loads((tmp_path / 'structured-review-report-buckets.json').read_text(encoding='utf-8'))
    assert 'visibility_gap' in report_buckets
    assert any(item['title'] == '附件处于可视域缺口，需人工复核原件' for item in report_buckets['visibility_gap'])
