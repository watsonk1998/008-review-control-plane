from __future__ import annotations

import asyncio
import json
from pathlib import Path
import re

from src.services.document_loader import DocumentLoader
from src.review.parser.attachment_indexer import build_attachment_index
from src.review import pipeline as review_pipeline
from src.review.pipeline import StructuredReviewExecutor
from src.review.report.pdf_exporter import _DEFAULT_PDF_CSS
from src.review.report.pdf_exporter import render_structured_review_pdf_sync
from src.review.report.report_builder import StructuredReviewReportBuilder
from src.review.schema import ConflictMatrix, HazardIdentificationMatrix, StructuredReviewMatrices, VisibilityAssessment


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
    assert result['reportHtml'].startswith('<article class="structured-report">')
    assert 'structured-report__overview-section' in result['reportHtml']
    assert 'class="structured-report__gap-item"' in result['reportHtml']
    assert 'class="structured-report__gap-item-title"' in result['reportHtml']
    assert 'class="structured-report__gap-item-list"' in result['reportHtml']
    assert 'class="structured-report__issue-card"' in result['reportHtml']
    assert 'class="structured-report__issue-card-section-title">问题描述<' in result['reportHtml']
    assert 'class="structured-report__issue-card-section-title">条文依据<' in result['reportHtml']
    assert 'class="structured-report__issue-card-law-list"' in result['reportHtml']
    assert 'class="structured-report__issue-card-law-requirements"' in result['reportHtml']
    assert '【1. 主要施工方案】 判定：' not in result['reportHtml']
    assert '识别章节： -' not in result['reportHtml']
    assert '补齐建议：建议' not in result['reportHtml']
    assert '问题描述 - ' not in result['reportHtml']
    assert '条文依据 - ' not in result['reportHtml']
    assert result['reportPrintCss']
    assert 'break-before: page' in result['reportPrintCss']
    assert 'page-break-before: always' in result['reportPrintCss']
    assert 'display: table-header-group' in result['reportPrintCss']
    assert 'overflow-wrap: anywhere' in result['reportPrintCss']
    assert '.structured-report__gap-item' in result['reportPrintCss']
    assert '.structured-report__issue-card-law-requirements' in result['reportPrintCss']
    assert 'border: 1px solid #e3ded2' in result['reportPrintCss']
    assert result['visibility']['manualReviewNeeded'] is True
    assert result['visibility']['parseMode'] == 'docx_structured'
    assert result['visibility']['manualReviewReason'] == 'title_detected_without_attachment_body'
    assert '# 施工组织设计形式审查报告' in result['reportMarkdown']
    assert '## 第一部分：审查结论与审查依据' in result['reportMarkdown']
    assert '### 2. 审查依据文件' in result['reportMarkdown']
    assert '#### 主要审查依据文件' in result['reportMarkdown']
    assert '#### 补充说明依据' in result['reportMarkdown']
    assert '系统附件识别与复核规则' in result['reportMarkdown']
    assert '系统附件可视域处理规则' not in result['reportMarkdown']
    assert '复核提示：正文提到了附件，但本次未识别到附件正文内容，需结合原件核对。' in result['reportMarkdown']
    assert '### 3. 审查总览表' in result['reportMarkdown']
    assert '<table class="structured-overview-table">' in result['reportMarkdown']
    assert '<thead><tr><th>序号</th><th>结构项</th><th>L1 问题摘要</th><th>L2 问题摘要</th><th>L3 问题摘要</th></tr></thead>' in result['reportMarkdown']
    overview_section = result['reportMarkdown'].split('## 第二部分：', 1)[0]
    assert '规范依据</th>' not in overview_section
    assert '文档对应章节</th>' not in overview_section
    assert '结构判定</th>' not in overview_section
    assert '第六章：' in result['reportMarkdown'] or '4.2节：' in result['reportMarkdown'] or '—' in result['reportMarkdown']
    assert '## 第二部分：L1 审查发现——合法合规与结构完整性' in result['reportMarkdown']
    assert '### 2.1 结构完整性与形式合规性' in result['reportMarkdown']
    assert '### 2.2 补充审查意见' in result['reportMarkdown']
    assert '## 第五部分：关键数据识别汇总' in result['reportMarkdown']
    assert '### 2. 附件可视域情况' not in result['reportMarkdown']
    assert '### 3. 施组结构完整性情况' not in result['reportMarkdown']
    assert '### 4. 章节结构情况' not in result['reportMarkdown']
    assert '### 5. 规则命中总体情况' not in result['reportMarkdown']
    assert '### 6. 主要冲突与联动提示' not in result['reportMarkdown']
    assert '## 第六部分：解析说明与复核提示' in result['reportMarkdown']
    assert '### 6.1 文档解析状态与预检结果' in result['reportMarkdown']
    assert '### 6.2 附件解析与关联情况' in result['reportMarkdown']
    assert '### 6.1 可视域与预检状态' not in result['reportMarkdown']
    assert '### 6.2 附件可视域断链' not in result['reportMarkdown']
    assert '### 6.3 待人工确认事项' in result['reportMarkdown']
    assert '条文依据' in result['reportMarkdown']
    assert '《建筑施工组织设计规范》GB/T 50502-2009' in result['reportMarkdown']
    assert '<table class="structured-completeness-table">' in result['reportMarkdown']
    assert '<thead><tr><th>序号</th><th>规范要求</th><th>规范依据</th><th>文档对应章节</th><th>结构判定</th><th>相关审查意见</th></tr></thead>' in result['reportMarkdown']
    assert '相关审查意见' in result['reportMarkdown']
    assert '定位说明' not in result['reportMarkdown']
    assert '| 序号 | 规范要求 | 规范依据 | 文档对应章节 | 结构判定 | 定位说明 |' not in result['reportMarkdown']
    assert '已识别到“第一章' not in result['reportMarkdown']
    assert '（位置 ' not in result['reportMarkdown']
    assert not re.search(r'位置\\s*\\d+', result['reportMarkdown'])
    assert '#### 缺项分析与补齐意见' in result['reportMarkdown']
    assert '【1. ' in result['reportMarkdown']
    assert '判定：' in result['reportMarkdown']
    assert '识别章节：' in result['reportMarkdown']
    assert '补齐建议：建议补齐“成本管理计划”专章或形成稳定章节标题。' in result['reportMarkdown']
    assert '---' in result['reportMarkdown']
    assert '```json' not in result['reportMarkdown']
    assert '- parse mode：docx_structured' not in result['reportMarkdown']
    assert 'ruleId' not in result['reportMarkdown']
    assert 'policy pack id' not in result['reportMarkdown']
    assert 'issue id' not in result['reportMarkdown']
    assert 'special_scheme_reference_requires_manual_confirmation' not in result['reportMarkdown']
    assert 'attachment_unparsed' not in result['reportMarkdown']
    assert 'referenced_only' not in result['reportMarkdown']
    assert 'blocked_by_visibility' not in result['reportMarkdown']
    assert 'hazard.monitoringSectionPresent' not in result['reportMarkdown']
    assert 'emergency.planTitles' not in result['reportMarkdown']
    assert 'demo' not in result['reportMarkdown']
    assert 'Demo' not in result['reportMarkdown']
    assert '当前风险/限制' not in result['reportMarkdown']
    assert '审查建议' not in result['reportMarkdown']
    assert '----------' not in result['reportMarkdown']
    assert '审核文件为 PDF，当前解析能力受限' not in result['reportMarkdown']
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
    assert len(result['matrices']['structureCompleteness']) == 12
    assert result['matrices']['structureCompleteness'][0]['itemKey'] == 'preparationBasis'
    assert result['matrices']['structureCompleteness'][-1]['itemKey'] == 'costManagementPlan'
    assert all(row['status'] in {'matched', 'partial', 'missing', 'blocked_by_visibility'} for row in result['matrices']['structureCompleteness'])
    cost_row = next(row for row in result['matrices']['structureCompleteness'] if row['itemKey'] == 'costManagementPlan')
    assert cost_row['status'] == 'missing'
    assert cost_row['matchedSections'] == []
    structure_issue = next(issue for issue in result['issues'] if issue['title'] == '施工组织设计核心章节不完整')
    assert all(span['sourceId'] == 'construction-《建筑施工组织设计规范》GB/T 50502-2009' for span in structure_issue['policyEvidence'])


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


def test_structured_review_executor_expands_hazardous_base_core_sections(tmp_path: Path):
    sample = tmp_path / 'hazardous_special_scheme_base_core.md'
    sample.write_text(
        '# 危大专项施工方案\n\n'
        '## 工程概况\n项目名称：危大专项核心核验\n'
        '## 编制依据\n依据专项审查要求编制。\n'
        '## 施工计划\n本专项计划分段实施。\n'
        '## 施工工艺技术\n明确施工方法。\n'
        '## 施工保证措施\n采取安全保证措施。\n'
        '## 应急处置措施\n设置应急联络。\n'
        '## 计算书\n附计算书。\n',
        encoding='utf-8',
    )
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=DummyLLM(), fast_adapter=None)
    result = executor.run_sync(
        task_id='hazardous-core-upgrade-test',
        query='对该危大专项方案执行正式结构化审查',
        source_document_path=str(sample),
        fixture_id='hazardous-core-upgrade-fixture',
        document_type='hazardous_special_scheme',
    )

    issue_titles = {issue['title'] for issue in result['issues']}
    assert '危大专项方案核心章节不完整' in issue_titles
    assert '危大专项方案缺少人员配备与分工章节' in issue_titles
    assert '危大专项方案缺少验收要求章节' in issue_titles
    assert '危大专项方案缺少风险辨识与分级章节' in issue_titles
    assert '危大专项方案缺少平面布置或周边环境章节' in issue_titles
    drawing_issue = next(issue for issue in result['issues'] if issue['title'] == '危大专项方案相关图纸需人工复核')
    assert drawing_issue['manualReviewNeeded'] is True
    assert drawing_issue['manualReviewReason'] == 'drawing_visibility_gap'
    assert drawing_issue['issueKind'] == 'visibility_gap'


def test_structured_review_executor_selects_foundation_pit_pack_and_keeps_drawing_gap_manual(tmp_path: Path):
    sample = tmp_path / 'foundation_pit_hazardous.md'
    sample.write_text(
        '# 基坑工程专项施工方案\n\n'
        '## 工程概况\n基坑工程概况。\n'
        '## 周边环境条件\n邻近道路及管线。\n'
        '## 编制依据\n依据规范编制。\n'
        '## 施工计划\n基坑工程施工进度安排。\n'
        '## 风险辨识与分级\n开展风险辨识。\n'
        '## 施工工艺技术\n包含支护、降水、土方开挖与加撑关系。\n'
        '## 施工保证措施\n包含监测监控措施。\n'
        '## 施工管理及作业人员配备和分工\n明确岗位职责。\n'
        '## 验收要求\n明确位移、沉降和轴力控制。\n'
        '## 应急处置措施\n设置应急联络。\n',
        encoding='utf-8',
    )
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=DummyLLM(), fast_adapter=None)
    result = executor.run_sync(
        task_id='foundation-pit-pack-test',
        query='对该危大专项方案执行正式结构化审查',
        source_document_path=str(sample),
        fixture_id='foundation-pit-pack-fixture',
        document_type='hazardous_special_scheme',
    )

    assert 'foundation_pit.base' in result['resolvedProfile']['policyPackIds']
    issue_titles = {issue['title'] for issue in result['issues']}
    assert '基坑工程监测图纸或监测章节需人工复核' in issue_titles
    issue = next(issue for issue in result['issues'] if issue['title'] == '基坑工程监测图纸或监测章节需人工复核')
    assert issue['manualReviewNeeded'] is True
    assert issue['manualReviewReason'] == 'drawing_visibility_gap'
    assert issue['issueKind'] == 'visibility_gap'


def test_structured_review_executor_selects_formwork_support_pack(tmp_path: Path):
    sample = tmp_path / 'formwork_support_hazardous.md'
    sample.write_text(
        '# 模板支撑体系专项施工方案\n\n'
        '## 工程概况\n模板支撑体系工程概况。\n'
        '## 编制依据\n依据规范编制。\n'
        '## 施工计划\n施工安排。\n'
        '## 风险辨识与分级\n开展风险辨识。\n'
        '## 施工管理及作业人员配备和分工\n明确岗位职责。\n'
        '## 验收要求\n明确验收程序。\n'
        '## 应急处置措施\n应急安排。\n',
        encoding='utf-8',
    )
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=DummyLLM(), fast_adapter=None)
    result = executor.run_sync(
        task_id='formwork-support-pack-test',
        query='对该危大专项方案执行正式结构化审查',
        source_document_path=str(sample),
        fixture_id='formwork-support-pack-fixture',
        document_type='hazardous_special_scheme',
    )

    assert 'formwork_support.base' in result['resolvedProfile']['policyPackIds']
    issue_titles = {issue['title'] for issue in result['issues']}
    assert '模板支撑体系关键工艺参数或浇筑顺序不完整' in issue_titles
    assert '模板支撑体系缺少可追溯计算依据' in issue_titles


def test_structured_review_executor_selects_steel_structure_pack_and_replaces_old_lifting_pack(tmp_path: Path):
    sample = tmp_path / 'steel_structure_installation_hazardous.md'
    sample.write_text(
        '# 钢结构安装工程专项施工方案\n\n'
        '## 工程概况\n钢结构安装工程概况。\n'
        '## 编制依据\n依据规范编制。\n'
        '## 施工计划\n施工安排。\n'
        '## 施工工艺技术\n钢构件安装；采用50T汽车吊；Q计=12.5t；吊装站位处地基承载力满足要求；设置平衡梁。\n'
        '## 技术参数\n构件重量、吊点和起升高度。\n'
        '## 工艺流程\n钢柱吊装、校正、临时固定。\n'
        '## 风险辨识与分级\n开展风险辨识。\n'
        '## 施工管理及作业人员配备和分工\n明确岗位职责。\n'
        '## 应急处置措施\n应急安排。\n'
        '## 计算书及相关施工图纸\n附计算书。\n',
        encoding='utf-8',
    )
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=DummyLLM(), fast_adapter=None)
    result = executor.run_sync(
        task_id='steel-structure-pack-test',
        query='对该危大专项方案执行正式结构化审查',
        source_document_path=str(sample),
        fixture_id='steel-structure-pack-fixture',
        document_type='hazardous_special_scheme',
    )

    selected_packs = set(result['resolvedProfile']['policyPackIds'])
    assert 'steel_structure_installation.base' in selected_packs
    assert 'lifting_installation_removal.base' in selected_packs
    assert 'lifting_operations.base' not in selected_packs
    issue_titles = {issue['title'] for issue in result['issues']}
    assert '钢结构安装缺少临时支撑或卸载条件' in issue_titles
    assert '钢结构安装图纸或验收章节需人工复核' in issue_titles


def test_structured_review_executor_selects_lifting_installation_removal_pack_for_hazardous_scheme(tmp_path: Path):
    sample = tmp_path / 'lifting_installation_removal_hazardous.md'
    sample.write_text(
        '# 起重吊装及安装拆卸工程专项施工方案\n\n'
        '## 工程概况\n起重吊装及安装拆卸工程概况。\n'
        '## 编制依据\n依据规范编制。\n'
        '## 施工计划\n施工安排。\n'
        '## 施工工艺技术\n采用汽车吊进行构件安装拆卸。\n'
        '## 风险辨识与分级\n开展风险辨识。\n'
        '## 施工管理及作业人员配备和分工\n明确岗位职责。\n'
        '## 验收要求\n明确验收程序。\n'
        '## 应急处置措施\n应急安排。\n',
        encoding='utf-8',
    )
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=DummyLLM(), fast_adapter=None)
    result = executor.run_sync(
        task_id='lifting-installation-removal-pack-test',
        query='对该危大专项方案执行正式结构化审查',
        source_document_path=str(sample),
        fixture_id='lifting-installation-removal-pack-fixture',
        document_type='hazardous_special_scheme',
    )

    selected_packs = set(result['resolvedProfile']['policyPackIds'])
    assert 'lifting_installation_removal.base' in selected_packs
    assert 'lifting_operations.base' not in selected_packs
    issue_titles = {issue['title'] for issue in result['issues']}
    assert '起重吊装及安装拆卸方案骨架不完整' in issue_titles
    assert '起重吊装及安装拆卸缺少站位承载依据' in issue_titles
    drawing_issue = next(issue for issue in result['issues'] if issue['title'] == '起重吊装及安装拆卸图纸需人工复核')
    assert drawing_issue['manualReviewNeeded'] is True
    assert drawing_issue['manualReviewReason'] == 'drawing_visibility_gap'


def test_structured_review_executor_keeps_old_lifting_pack_for_construction_org(tmp_path: Path):
    sample = tmp_path / 'construction_org_lifting.md'
    sample.write_text(
        '# 施工组织设计\n\n'
        '## 工程概况\n起重吊装工程概况。\n'
        '## 编制依据\n依据规范编制。\n'
        '## 施工部署\n施工安排。\n'
        '## 施工工艺\n采用汽车吊吊装。\n',
        encoding='utf-8',
    )
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=DummyLLM(), fast_adapter=None)
    result = executor.run_sync(
        task_id='construction-org-lifting-pack-test',
        query='对该施工组织设计执行正式结构化审查',
        source_document_path=str(sample),
        fixture_id='construction-org-lifting-pack-fixture',
        document_type='construction_org',
        discipline_tags=['lifting_operations'],
    )

    selected_packs = set(result['resolvedProfile']['policyPackIds'])
    assert 'lifting_operations.base' in selected_packs
    assert 'lifting_installation_removal.base' not in selected_packs


def test_structured_review_executor_selects_distribution_network_base_and_power_outage_work(tmp_path: Path):
    sample = tmp_path / 'distribution_network_power_outage.md'
    sample.write_text(
        '# 配网工程停电施工作业专项施工方案\n\n'
        '## 工程概况\n配网改造项目概况。\n'
        '## 编制依据\n依据配网停电作业要求编制。\n'
        '## 施工计划\n停电窗口内实施。\n'
        '## 施工工艺技术\n执行停送电作业流程。\n'
        '## 安全保证措施\n仅提供概括性措施。\n',
        encoding='utf-8',
    )
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=DummyLLM(), fast_adapter=None)
    result = executor.run_sync(
        task_id='distribution-network-power-outage-test',
        query='对该配网工程专项施工方案执行正式结构化审查',
        source_document_path=str(sample),
        fixture_id='distribution-network-power-outage-fixture',
        document_type='distribution_network_special_scheme',
        discipline_tags=['temporary_power'],
    )

    selected_packs = set(result['resolvedProfile']['policyPackIds'])
    assert 'distribution_network_special_scheme.base' in selected_packs
    assert 'power_outage_work.base' in selected_packs
    assert 'temporary_power.base' not in selected_packs
    assert 'power_outage_work' in result['resolvedProfile']['disciplineTags']
    assert 'temporary_power' not in result['resolvedProfile']['disciplineTags']
    issue_titles = {issue['title'] for issue in result['issues']}
    assert '临时用电/停送电控制链路不完整' in issue_titles


def test_structured_review_executor_selects_scaffold_pack(tmp_path: Path):
    sample = tmp_path / 'scaffold_hazardous.md'
    sample.write_text(
        '# 脚手架工程专项施工方案\n\n'
        '## 工程概况\n脚手架工程概况。\n'
        '## 编制依据\n依据规范编制。\n'
        '## 施工计划\n施工安排。\n'
        '## 技术参数\n架体高度及基础参数。\n'
        '## 施工工艺技术\n脚手架搭设方案。\n'
        '## 风险辨识与分级\n开展风险辨识。\n'
        '## 验收要求\n明确验收程序。\n'
        '## 应急处置措施\n应急安排。\n',
        encoding='utf-8',
    )
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=DummyLLM(), fast_adapter=None)
    result = executor.run_sync(
        task_id='scaffold-pack-test',
        query='对该危大专项方案执行正式结构化审查',
        source_document_path=str(sample),
        fixture_id='scaffold-pack-fixture',
        document_type='hazardous_special_scheme',
    )

    assert 'scaffold.base' in result['resolvedProfile']['policyPackIds']
    issue_titles = {issue['title'] for issue in result['issues']}
    assert '脚手架工程缺少连墙件或防坠落装置说明' in issue_titles
    assert '脚手架工程监测或验收要求不完整' in issue_titles


def test_structured_review_executor_selects_demolition_pack(tmp_path: Path):
    sample = tmp_path / 'demolition_hazardous.md'
    sample.write_text(
        '# 拆除工程专项施工方案\n\n'
        '## 工程概况\n拆除工程概况。\n'
        '## 编制依据\n依据规范编制。\n'
        '## 施工计划\n施工安排。\n'
        '## 工艺流程\n拆除顺序为先围护后主体。\n'
        '## 施工工艺技术\n拆除施工方法。\n'
        '## 风险辨识与分级\n开展风险辨识。\n'
        '## 应急处置措施\n应急安排。\n',
        encoding='utf-8',
    )
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=DummyLLM(), fast_adapter=None)
    result = executor.run_sync(
        task_id='demolition-pack-test',
        query='对该危大专项方案执行正式结构化审查',
        source_document_path=str(sample),
        fixture_id='demolition-pack-fixture',
        document_type='hazardous_special_scheme',
    )

    assert 'demolition.base' in result['resolvedProfile']['policyPackIds']
    issue_titles = {issue['title'] for issue in result['issues']}
    assert '拆除工程缺少保留结构或平台控制要求' in issue_titles
    assert '拆除工程缺少临时支撑或吊运计算依据' in issue_titles


def test_structured_review_executor_selects_underground_excavation_pack(tmp_path: Path):
    sample = tmp_path / 'underground_excavation_hazardous.md'
    sample.write_text(
        '# 暗挖工程专项施工方案\n\n'
        '## 工程概况\n暗挖工程概况。\n'
        '## 编制依据\n依据规范编制。\n'
        '## 施工计划\n施工安排。\n'
        '## 技术参数\n开挖断面尺寸。\n'
        '## 施工工艺技术\n盾构推进。\n'
        '## 风险辨识与分级\n开展风险辨识。\n'
        '## 应急处置措施\n应急安排。\n',
        encoding='utf-8',
    )
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=DummyLLM(), fast_adapter=None)
    result = executor.run_sync(
        task_id='underground-pack-test',
        query='对该危大专项方案执行正式结构化审查',
        source_document_path=str(sample),
        fixture_id='underground-pack-fixture',
        document_type='hazardous_special_scheme',
    )

    assert 'underground_excavation.base' in result['resolvedProfile']['policyPackIds']
    issue_titles = {issue['title'] for issue in result['issues']}
    assert '暗挖工程缺少地下水控制措施' in issue_titles
    drawing_issue = next(issue for issue in result['issues'] if issue['title'] == '暗挖工程监测图纸需人工复核')
    assert drawing_issue['manualReviewNeeded'] is True
    assert drawing_issue['manualReviewReason'] == 'drawing_visibility_gap'


def test_structured_review_executor_selects_curtain_wall_installation_pack(tmp_path: Path):
    sample = tmp_path / 'curtain_wall_hazardous.md'
    sample.write_text(
        '# 建筑幕墙安装工程专项施工方案\n\n'
        '## 工程概况\n建筑幕墙安装工程概况。\n'
        '## 编制依据\n依据规范编制。\n'
        '## 施工计划\n施工安排。\n'
        '## 施工平面布置\n场地平面布置。\n'
        '## 风险辨识与分级\n开展风险辨识。\n'
        '## 验收要求\n明确验收程序。\n'
        '## 应急处置措施\n应急安排。\n',
        encoding='utf-8',
    )
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=DummyLLM(), fast_adapter=None)
    result = executor.run_sync(
        task_id='curtain-wall-pack-test',
        query='对该危大专项方案执行正式结构化审查',
        source_document_path=str(sample),
        fixture_id='curtain-wall-pack-fixture',
        document_type='hazardous_special_scheme',
    )

    assert 'curtain_wall_installation.base' in result['resolvedProfile']['policyPackIds']
    issue_titles = {issue['title'] for issue in result['issues']}
    assert '建筑幕墙安装设施或防护措施不完整' in issue_titles
    drawing_issue = next(issue for issue in result['issues'] if issue['title'] == '建筑幕墙安装图纸或验收章节需人工复核')
    assert drawing_issue['manualReviewNeeded'] is True
    assert drawing_issue['manualReviewReason'] == 'drawing_visibility_gap'


def test_structured_review_executor_selects_manual_bored_pile_pack(tmp_path: Path):
    sample = tmp_path / 'manual_bored_pile_hazardous.md'
    sample.write_text(
        '# 人工挖孔桩工程专项施工方案\n\n'
        '## 工程概况\n人工挖孔桩工程概况。\n'
        '## 编制依据\n依据规范编制。\n'
        '## 施工计划\n施工安排。\n'
        '## 施工工艺技术\n厚度超过 2m 的砂层，需重点核验。\n'
        '## 风险辨识与分级\n开展风险辨识。\n'
        '## 应急处置措施\n应急安排。\n',
        encoding='utf-8',
    )
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=DummyLLM(), fast_adapter=None)
    result = executor.run_sync(
        task_id='manual-bored-pile-pack-test',
        query='对该危大专项方案执行正式结构化审查',
        source_document_path=str(sample),
        fixture_id='manual-bored-pile-pack-fixture',
        document_type='hazardous_special_scheme',
    )

    assert 'manual_bored_pile.base' in result['resolvedProfile']['policyPackIds']
    issue_titles = {issue['title'] for issue in result['issues']}
    assert '人工挖孔桩缺少跳挖或分序要求' in issue_titles
    assert '人工挖孔桩缺少防中毒窒息或防触电措施' in issue_titles
    forbidden_issue = next(issue for issue in result['issues'] if issue['title'] == '人工挖孔桩禁用条件需人工复核')
    assert forbidden_issue['manualReviewNeeded'] is True
    assert forbidden_issue['manualReviewReason'] == 'forbidden_condition_requires_manual_confirmation'


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
    assert '审核文件为 PDF，当前解析能力受限，可能存在审查不完整或判定偏差，建议结合原件人工复核。' in result['reportMarkdown']
    assert result['reportMarkdown'].count('审核文件为 PDF，当前解析能力受限') == 1
    assert '## 第六部分：解析说明与复核提示' in result['reportMarkdown']
    assert '### 6.3 待人工确认事项' in result['reportMarkdown']
    assert '当前解析路径受限' not in result['reportMarkdown']
    assert '受限解析路径' not in result['reportMarkdown']
    assert 'parser-limited' not in result['reportMarkdown']
    assert 'working_at_height' not in result['reportMarkdown']
    assert 'gas_area_ops' not in result['reportMarkdown']
    assert 'hot_work' not in result['reportMarkdown']
    assert 'temporary_power' not in result['reportMarkdown']
    assert 'calculationBook' not in result['reportMarkdown']
    assert '高处作业' in result['reportMarkdown'] or '煤气区域作业' in result['reportMarkdown']
    assert '施工部署/施工计划' in result['reportMarkdown'] or '监测监控' in result['reportMarkdown']
    assert result['reportMarkdown'].count('尚无法稳定确认“') <= 2
    assert '以下结构性章节尚无法稳定确认是否真实缺失' in result['reportMarkdown']
    assert '当前尚未稳定提取以下关键参数或支撑信息' in result['reportMarkdown']
    assert '另命中若干相关章节，详见结构化结果' in result['reportMarkdown']
    assert '（位置 ' not in result['reportMarkdown']
    assert '系统附件可视域处理规则' not in result['reportMarkdown']
    assert 'demo' not in result['reportMarkdown']
    assert any(
        issue['applicabilityState'] == 'blocked_by_missing_fact' and issue['missingFactKeys']
        for issue in result['issues']
    )
    blocked_structure_rows = [row for row in result['matrices']['structureCompleteness'] if row['status'] == 'blocked_by_visibility']
    assert blocked_structure_rows
    assert any(row['itemKey'] == 'costManagementPlan' for row in blocked_structure_rows)
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


def test_pdf_exporter_uses_landscape_a4_for_expert_report():
    assert 'size: A4 landscape;' in _DEFAULT_PDF_CSS


def test_pdf_exporter_renders_html_with_print_css(tmp_path: Path):
    output = tmp_path / 'report.pdf'
    result = render_structured_review_pdf_sync(
        report_html=(
            '<article class="structured-report">'
            '<section class="structured-report__section">'
            '<h2 class="structured-report__section-title">第一部分</h2>'
            '<section class="structured-report__overview-section">'
            '<h3 class="structured-report__subsection-title">3. 审查总览表</h3>'
            '<table class="structured-overview-table"><thead><tr><th>序号</th><th>结构项</th><th>L1 问题摘要</th><th>L2 问题摘要</th><th>L3 问题摘要</th></tr></thead>'
            '<tbody><tr><td>1</td><td>编制依据</td><td>—</td><td>—</td><td>—</td></tr></tbody></table>'
            '</section>'
            '</section>'
            '</article>'
        ),
        report_print_css=(
            '.structured-report{padding:20px;}'
            '.structured-report__overview-section{break-before:page;page-break-before:always;}'
            'thead{display:table-header-group;}'
            'td,th{white-space:normal;word-break:break-word;overflow-wrap:anywhere;}'
        ),
        output_path=output,
        title='测试报告',
    )
    assert result == output
    assert output.exists()
    assert output.stat().st_size > 0


def test_pipeline_passes_html_and_css_to_pdf_exporter(monkeypatch, tmp_path: Path):
    captured: dict[str, str] = {}

    async def fake_render_structured_review_pdf(*, report_html, report_print_css, output_path, title=None, markdown_fallback=None):
        captured['report_html'] = report_html
        captured['report_print_css'] = report_print_css
        captured['markdown_fallback'] = markdown_fallback or ''
        output_path.write_bytes(b'%PDF-1.4 fake')
        return output_path

    monkeypatch.setattr(review_pipeline, 'render_structured_review_pdf', fake_render_structured_review_pdf)
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=DummyLLM(), fast_adapter=None)

    def write_text_artifact(name: str, content: str, suffix: str) -> str:
        path = tmp_path / f'{name}{suffix}'
        path.write_text(content, encoding='utf-8')
        return str(path)

    def write_json_artifact(name: str, data) -> str:
        path = tmp_path / f'{name}.json'
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        return str(path)

    def write_binary_artifact(name: str, data: bytes, suffix: str) -> str:
        path = tmp_path / f'{name}{suffix}'
        path.write_bytes(data)
        return str(path)

    result = executor.run_sync(
        task_id='structured-review-pdf-path-test',
        query='对该施工组织设计执行正式结构化审查',
        source_document_path=str(SAMPLE_DOC),
        fixture_id='supervision-cold-rolling-construction-plan',
        write_text_artifact=write_text_artifact,
        write_json_artifact=write_json_artifact,
        write_binary_artifact=write_binary_artifact,
    )
    assert captured['report_html'].startswith('<article class="structured-report">')
    assert 'structured-report__gap-item' in captured['report_html']
    assert 'break-before: page' in captured['report_print_css']
    assert '# 施工组织设计形式审查报告' in captured['markdown_fallback']
    assert result['artifactIndex']


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

    non_limited_reference_only = [{'id': 'b3-ref', 'text': '详见附件3。'}]
    attachments, _ = build_attachment_index(non_limited_reference_only, parser_limited=False, file_type='docx')
    assert attachments[0]['visibility'] == 'referenced_only'
    assert attachments[0]['reason'] == 'reference_detected_without_attachment_body'

    explicit_missing_blocks = [{'id': 'b4', 'text': '附件4：吊装验算书（后补，暂缺）'}]
    attachments, _ = build_attachment_index(explicit_missing_blocks, parser_limited=False, file_type='docx')
    assert attachments[0]['visibility'] == 'missing'
    assert attachments[0]['reason'] == 'explicit_missing_marker'


def test_structured_review_parser_limited_pdf_zero_parsed_attachments_frontloads_l0_gate():
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=DummyLLM(), fast_adapter=None)
    result = executor.run_sync(
        task_id='structured-review-pdf-zero-parsed-attachments',
        query='对该危大专项方案执行正式结构化审查',
        source_document_path=str(SAMPLE_PDF),
        fixture_id='cn_hz_pdf_unknown_visibility_ci',
        document_type='hazardous_special_scheme',
        discipline_tags=['lifting_operations'],
    )

    assert result['visibility']['parseMode'] == 'pdf_text_only'
    assert result['visibility']['manualReviewNeeded'] is True
    assert result['visibility']['preflight']['gateDecision'] == 'manual_review_required'
    assert result['visibility']['counts']['parsed'] == 0
    assert result['visibility']['counts']['unknown'] >= 1
    assert 'parser_limited_pdf' in result['visibility']['preflight']['blockingReasons']
    assert result['summary']['visibilitySummary']['manualReviewNeeded'] is True


def test_structured_review_artifacts_keep_visibility_parity_for_unknown_and_attachment_unparsed(tmp_path: Path):
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=DummyLLM(), fast_adapter=None)

    def write_json_artifact(name: str, payload):
        path = tmp_path / f'{name}.json'
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        return str(path)

    def write_text_artifact(name: str, content: str, suffix: str):
        path = tmp_path / f'{name}{suffix}'
        path.write_text(content, encoding='utf-8')
        return str(path)

    pdf_result = asyncio.run(
        executor.run(
            task_id='structured-review-l0-parity-pdf',
            query='对该危大专项方案执行正式结构化审查',
            source_document_path=str(SAMPLE_PDF),
            fixture_id='cn_hz_pdf_unknown_visibility_ci',
            document_type='hazardous_special_scheme',
            discipline_tags=['lifting_operations'],
            write_json_artifact=write_json_artifact,
            write_text_artifact=write_text_artifact,
        )
    )
    pdf_l0_payload = json.loads((tmp_path / 'structured-review-l0-visibility.json').read_text(encoding='utf-8'))
    assert pdf_l0_payload['visibility'] == pdf_result['visibility']
    assert pdf_l0_payload['visibility']['counts']['unknown'] >= 1
    assert pdf_l0_payload['visibility']['counts']['missing'] == 0

    docx_tmp = tmp_path / 'docx-run'
    docx_tmp.mkdir()

    def write_docx_json_artifact(name: str, payload):
        path = docx_tmp / f'{name}.json'
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        return str(path)

    def write_docx_text_artifact(name: str, content: str, suffix: str):
        path = docx_tmp / f'{name}{suffix}'
        path.write_text(content, encoding='utf-8')
        return str(path)

    docx_result = asyncio.run(
        executor.run(
            task_id='structured-review-l0-parity-docx',
            query='对该施工组织设计执行正式结构化审查',
            source_document_path=str(SAMPLE_DOC),
            fixture_id='supervision-cold-rolling-construction-plan',
            write_json_artifact=write_docx_json_artifact,
            write_text_artifact=write_docx_text_artifact,
        )
    )
    docx_l0_payload = json.loads((docx_tmp / 'structured-review-l0-visibility.json').read_text(encoding='utf-8'))
    assert docx_l0_payload['visibility'] == docx_result['visibility']
    assert docx_l0_payload['visibility']['counts']['attachment_unparsed'] >= 1
    assert docx_l0_payload['visibility']['counts']['missing'] == 0


def test_structured_review_frontloads_weak_key_section_structure_into_l0_gate(tmp_path: Path):
    sample = tmp_path / 'construction_org_duplicate_key_section.md'
    sample.write_text(
        '# 施工组织设计\n\n'
        '## 第一章 工程概况\n项目名称：重复结构测试\n项目编号：STRUCT-DEMO\n'
        '## 第二章 工程概况\n项目名称：重复结构测试（重复）\n'
        '## 第三章 施工部署\n安排如下。\n'
        '## 第四章 施工进度计划\n工期 30 天。\n'
        '## 第五章 资源配置计划\n劳动力 20 人。\n'
        '## 第六章 安全保证措施\n执行标准措施。\n'
        '## 第七章 应急预案\n火灾应急预案。\n'
        '## 第八章 施工总平面布置\n见正文。\n',
        encoding='utf-8',
    )
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=DummyLLM(), fast_adapter=None)
    result = executor.run_sync(
        task_id='structured-review-weak-structure-signal',
        query='对该施工组织设计执行正式结构化审查',
        source_document_path=str(sample),
        fixture_id='structured-review-weak-structure-signal',
        document_type='construction_org',
    )

    duplicate_issue = next(issue for issue in result['issues'] if issue['title'] == '章节结构存在重复标题，正式审查定位不稳定')
    duplicate_rule = next(row for row in result['matrices']['ruleHits'] if row['ruleId'] == 'construction_org_duplicate_sections')
    unresolved_fact = next(fact for fact in result['unresolvedFacts'] if fact['factKey'] == 'project.duplicateSections')

    assert result['visibility']['manualReviewNeeded'] is True
    assert result['visibility']['manualReviewReason'] == 'weak_section_structure_signal'
    assert result['visibility']['preflight']['gateDecision'] == 'manual_review_required'
    assert 'weak_section_structure_signal' in result['visibility']['preflight']['blockingReasons']
    assert result['visibility']['preflight']['checklist'][2]['status'] == 'manual_review_required'
    assert result['visibility']['counts']['missing'] == 0
    assert result['summary']['visibilitySummary']['manualReviewNeeded'] is True
    assert duplicate_issue['issueKind'] == 'visibility_gap'
    assert duplicate_issue['applicabilityState'] == 'blocked_by_visibility'
    assert duplicate_issue['manualReviewReason'] == 'weak_section_structure_signal'
    assert 'weak_section_structure_signal' in duplicate_issue['blockingReasons']
    assert duplicate_rule['applicabilityState'] == 'blocked_by_visibility'
    assert duplicate_rule['missingFactKeys'] == ['project.duplicateSections']
    assert 'weak_section_structure_signal' in duplicate_rule['blockingReasons']
    assert unresolved_fact['visibilityLimited'] is True
    assert 'construction_org_duplicate_sections' in unresolved_fact['blockingRuleIds']
    assert duplicate_issue['id'] in unresolved_fact['blockingIssueIds']


def test_structured_review_generic_special_scheme_mention_stays_partial_not_hard_defect(tmp_path: Path):
    sample = tmp_path / 'construction_org_generic_special_scheme.md'
    sample.write_text(
        '# 施工组织设计\n\n'
        '## 工程概况\n项目名称：专项方案挂接待确认\n项目编号：SPECIAL-DEMO\n'
        '存在起重吊装作业。\n'
        '## 施工部署\n按计划实施。\n'
        '## 施工进度计划\n工期 20 天。\n'
        '## 资源配置计划\n劳动力 20 人。\n'
        '## 安全保证措施\n执行标准安全措施。\n'
        '## 应急预案\n起重吊装应急处置预案。\n'
        '## 施工总平面布置\n正文可见。\n'
        '本工程另有专项施工方案，详见既有资料目录。\n',
        encoding='utf-8',
    )
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=DummyLLM(), fast_adapter=None)
    result = executor.run_sync(
        task_id='structured-review-generic-special-scheme',
        query='对该施工组织设计执行正式结构化审查',
        source_document_path=str(sample),
        fixture_id='structured-review-generic-special-scheme',
        document_type='construction_org',
        discipline_tags=['lifting_operations'],
    )

    special_rule = next(row for row in result['matrices']['ruleHits'] if row['ruleId'] == 'construction_org_special_scheme_gap')
    special_issue = next(issue for issue in result['issues'] if issue['title'] == '高风险作业已识别，但专项方案挂接不清')

    assert special_rule['status'] == 'manual_review_needed'
    assert special_rule['applicabilityState'] == 'partial'
    assert 'manual_confirmation_required' in special_rule['blockingReasons']
    assert special_issue['manualReviewNeeded'] is True
    assert special_issue['applicabilityState'] == 'partial'
    assert special_issue['issueKind'] != 'hard_defect'
    assert 'manual_confirmation_required' in special_issue['blockingReasons']


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


def test_structured_review_parser_limited_emergency_gap_stays_evidence_gap_with_traceability():
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=DummyLLM(), fast_adapter=None)
    result = executor.run_sync(
        task_id='structured-review-parser-limited-emergency-gap',
        query='对该施工组织设计执行正式结构化审查',
        source_document_path=str(SAMPLE_PUHUA_PDF),
        fixture_id='puhua-review-fixture',
        document_type='construction_org',
        discipline_tags=['lifting_operations', 'temporary_power', 'hot_work'],
    )

    emergency_rule = next(row for row in result['matrices']['ruleHits'] if row['ruleId'] == 'construction_org_emergency_plan_targeted')
    emergency_issue = next(issue for issue in result['issues'] if issue['title'] == '应急预案针对性不足')
    emergency_fact = next(fact for fact in result['unresolvedFacts'] if fact['factKey'] == 'emergency.planTitles')

    assert emergency_rule['applicabilityState'] == 'blocked_by_missing_fact'
    assert emergency_rule['missingFactKeys'] == ['emergency.planTitles']
    assert 'missing_fact' in emergency_rule['blockingReasons']
    assert 'parser_limited_source' in emergency_rule['blockingReasons']
    assert emergency_issue['issueKind'] == 'evidence_gap'
    assert emergency_issue['applicabilityState'] == 'blocked_by_missing_fact'
    assert emergency_issue['evidenceMissing'] is True
    assert emergency_issue['missingFactKeys'] == ['emergency.planTitles']
    assert 'missing_fact' in emergency_issue['blockingReasons']
    assert 'parser_limited_source' in emergency_issue['blockingReasons']
    assert 'construction_org_emergency_plan_targeted' in emergency_fact['blockingRuleIds']
    assert emergency_issue['id'] in emergency_fact['blockingIssueIds']


def test_structured_review_parser_limited_empty_attachment_matrix_keeps_blocked_issue_traceability():
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=DummyLLM(), fast_adapter=None)
    result = executor.run_sync(
        task_id='structured-review-parser-limited-empty-attachment-matrix',
        query='对该施工组织设计执行正式结构化审查',
        source_document_path=str(SAMPLE_PUHUA_PDF),
        fixture_id='puhua-review-fixture',
        document_type='construction_org',
        discipline_tags=['lifting_operations', 'temporary_power', 'hot_work'],
    )

    assert result['visibility']['attachmentCount'] == 0
    assert result['matrices']['attachmentVisibility'] == []
    assert result['visibility']['manualReviewNeeded'] is True
    blocked_issue = next(issue for issue in result['issues'] if issue['applicabilityState'] == 'blocked_by_missing_fact')
    traced_fact = next(fact for fact in result['unresolvedFacts'] if blocked_issue['id'] in fact['blockingIssueIds'])

    assert blocked_issue['missingFactKeys']
    assert blocked_issue['blockingReasons']
    assert traced_fact['blockingRuleIds']
    assert traced_fact['blockingIssueIds']


def test_structured_review_blocked_evidence_spans_expose_provenance_and_gap_reason():
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=DummyLLM(), fast_adapter=None)
    result = executor.run_sync(
        task_id='structured-review-evidence-provenance',
        query='对该危大专项方案执行正式结构化审查',
        source_document_path=str(SAMPLE_PDF),
        fixture_id='cn_hz_pdf_unknown_visibility_ci',
        document_type='hazardous_special_scheme',
        discipline_tags=['lifting_operations'],
    )

    calc_issue = next(issue for issue in result['issues'] if issue['title'] == '专项方案缺少可追溯验算依据')
    assert calc_issue['applicabilityState'] == 'blocked_by_missing_fact'
    assert calc_issue['blockingReasons']
    assert calc_issue['docEvidence'][0]['sourceProvenance'].startswith('document:source.pdf:block:')
    assert calc_issue['docEvidence'][0]['evidenceGapReason'] == 'parser_limited_source'
    assert calc_issue['policyEvidence'][0]['sourceProvenance']
    assert calc_issue['policyEvidence'][0]['evidenceGapReason'] == 'parser_limited_source'


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

    def write_binary_artifact(name: str, content: bytes, suffix: str):
        path = tmp_path / f'{name}{suffix}'
        path.write_bytes(content)
        return str(path)

    result = asyncio.run(
        executor.run(
            task_id='structured-review-artifacts',
            query='对该施工组织设计执行正式结构化审查',
            source_document_path=str(SAMPLE_DOC),
            fixture_id='supervision-cold-rolling-construction-plan',
            write_json_artifact=write_json_artifact,
            write_text_artifact=write_text_artifact,
            write_binary_artifact=write_binary_artifact,
        )
    )

    artifact_categories = {artifact['category'] for artifact in result['artifactIndex']}
    assert {'parse', 'facts', 'rule_hits', 'candidates', 'result', 'matrices', 'report'}.issubset(artifact_categories)
    artifact_names = {artifact['name'] for artifact in result['artifactIndex']}
    assert 'structured-review-l0-visibility' in artifact_names
    assert 'structure-completeness-matrix' in artifact_names
    assert 'structured-review-report-buckets' in artifact_names
    assert 'structured-review-report' in artifact_names
    assert any(artifact['fileName'].endswith('.html') for artifact in result['artifactIndex'])
    assert any(artifact['fileName'].endswith('.css') for artifact in result['artifactIndex'])
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
    assert result_payload['reportHtml']
    assert result_payload['reportPrintCss']
    assert result_payload['visibility'] == l0_payload['visibility']
    assert result_payload['visibility']['preflight']['gateDecision'] == 'manual_review_required'
    report_buckets = json.loads((tmp_path / 'structured-review-report-buckets.json').read_text(encoding='utf-8'))
    assert 'visibility_gap' in report_buckets
    assert any(item['title'] == '附件处于可视域缺口，需人工复核原件' for item in report_buckets['visibility_gap'])
    pdf_artifact = next(artifact for artifact in result['artifactIndex'] if artifact['fileName'].endswith('.pdf'))
    assert pdf_artifact['category'] == 'report'
    assert pdf_artifact['mediaType'] == 'application/pdf'
    assert pdf_artifact['primary'] is True
    assert (tmp_path / 'structured-review-report.html').stat().st_size > 0
    assert (tmp_path / 'structured-review-report.print.css').stat().st_size > 0
    assert (tmp_path / 'structured-review-report.pdf').stat().st_size > 0


def test_report_builder_summary_conclusion_mapping():
    builder = StructuredReviewReportBuilder()
    matrices = StructuredReviewMatrices(
        hazardIdentification=HazardIdentificationMatrix(values={}),
        ruleHits=[],
        conflicts=ConflictMatrix(values={}),
        attachmentVisibility=[],
        sectionStructure=[],
        issueLayerCounts={},
    )

    hard_issue = type('Issue', (), {
        'layer': type('Layer', (), {'value': 'L1'})(),
        'severity': 'medium',
        'issueKind': 'hard_defect',
        'manualReviewNeeded': False,
        'applicabilityState': 'applies',
    })()
    hard_summary = builder.build_summary(
        document_type='construction_org',
        selected_packs=['construction_org.base'],
        issues=[hard_issue],
        matrices=matrices,
        visibility=VisibilityAssessment(),
        parse_warnings=[],
        unresolved_facts=[],
    )
    assert hard_summary.overallConclusion == '修改后重新报审'

    manual_visibility = VisibilityAssessment(manualReviewNeeded=True)
    manual_summary = builder.build_summary(
        document_type='construction_org',
        selected_packs=['construction_org.base'],
        issues=[],
        matrices=matrices,
        visibility=manual_visibility,
        parse_warnings=[],
        unresolved_facts=[],
    )
    assert manual_summary.overallConclusion == '需人工复核'

    pass_summary = builder.build_summary(
        document_type='construction_org',
        selected_packs=['construction_org.base'],
        issues=[],
        matrices=matrices,
        visibility=VisibilityAssessment(),
        parse_warnings=[],
        unresolved_facts=[],
    )
    assert pass_summary.overallConclusion == '合格通过'
