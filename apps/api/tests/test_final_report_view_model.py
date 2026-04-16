from __future__ import annotations

from src.review.contracts import FinalReportPacket, FindingItem
from src.review.report.final_report_view_model import FinalReportRenderer


def _support_issue(issue_id: str, title: str, excerpt: str | None = None):
    doc_evidence = []
    if excerpt is not None:
        doc_evidence.append({'excerpt': excerpt})
    return {
        'id': issue_id,
        'title': title,
        'summary': f'{title} 的支撑描述',
        'docEvidence': doc_evidence,
        'policyEvidence': [
            {
                'sourceId': 'construction-《建设工程安全生产管理条例》',
                'clauseTitle': '方案编制主体合格',
            }
        ],
        'recommendation': ['补齐并重新复核。'],
    }


def test_final_report_view_model_builds_sections_and_compact_chapter_matrix():
    renderer = FinalReportRenderer()
    packet = FinalReportPacket(
        review_id='r1',
        executive_summary=(
            '本次审查已由专业主审组件裁决完成，总体评级结论为：**不通过**。'
        ),
        all_findings=[
            FindingItem(
                id='ISSUE-001',
                title='停电施工作业专项章节不完整',
                severity='high',
                category='chapter_completeness',
                summary='专项章节缺失。',
                suggestion='补齐专项章节。',
                raw_data={
                    'module_name': 'structure_completeness',
                    'docEvidence': [{'excerpt': '第3章 3.1.2 计划停电工作时间'}],
                    'policyEvidence': [
                        {'sourceId': 'construction-《危险性较大的分部分项工程专项施工方案编制指南》（建办质〔2021〕48号）', 'clauseTitle': '停电施工作业专项补充目录要求'},
                        {'sourceId': 'power-grid-监理工程师对停电施工方案的审核规则及要点', 'clauseTitle': '停电范围'},
                    ],
                },
            ),
            FindingItem(
                id='ISSUE-002',
                title='计划停电时间核心参数缺失',
                severity='high',
                category='parameter_consistency',
                summary='关键时间参数缺失。',
                suggestion='补齐停电起止时间。',
                raw_data={'module_name': 'parameter_consistency'},
            ),
            FindingItem(
                id='ISSUE-003',
                title='施工单位主体名称前后矛盾',
                severity='medium',
                category='compliance',
                summary='主体名称不一致。',
                suggestion='统一主体名称。',
                raw_data={'module_name': 'legality_compliance'},
            ),
            FindingItem(
                id='H-NORM-SUM-001',
                title='编制依据现行有效性核验',
                severity='info',
                category='evidence_verification',
                summary='共核验 2 项编制依据。',
                raw_data={
                    'module_name': 'evidence_validation',
                    'normativeValidityChecks': [
                        {
                            'title': '《中国南方电网有限责任公司电力安全工作规程》Q/CSG 510001-2015',
                            'status': 'current',
                        },
                        {
                            'title': '《深圳电网工程安全文明施工标准（2019年版）》',
                            'status': 'unknown',
                        },
                    ],
                },
            ),
        ],
    )
    support_result = {
        'summary': {
            'documentType': 'distribution_network_special_scheme',
            'selectedPacks': ['distribution_network_special_scheme.base', 'power_outage_work.base'],
        },
        'resolvedProfile': {
            'policyPackIds': ['distribution_network_special_scheme.base', 'power_outage_work.base'],
        },
        'issues': [
            _support_issue('ISSUE-001', '停电施工作业专项章节不完整', '第3章 3.1.2 计划停电工作时间'),
            _support_issue('ISSUE-002', '计划停电时间核心参数缺失', '3.1.2 计划停电工作时间：后无任何内容'),
            _support_issue('ISSUE-003', '施工单位主体名称前后矛盾', '第2章 2.1.1 工程简介'),
        ],
        'matrices': {
            'structureCompleteness': [
                {
                    'itemKey': 'powerOutageScope',
                    'requirementLabel': '停电范围',
                    'basisClause': '停电施工作业专项补充要求',
                    'basisRequirement': '应明确停电范围',
                    'status': 'missing',
                    'matchedSections': [],
                    'analysis': '未识别到稳定对应章节。',
                    'reportExcerpt': '建议补齐停电范围。',
                },
                {
                    'itemKey': 'powerOutageWorkContent',
                    'requirementLabel': '作业内容',
                    'basisClause': '停电施工作业专项补充要求',
                    'basisRequirement': '应明确作业内容',
                    'status': 'partial',
                    'matchedSections': [{'title': '第3章 本次停电作业内容及安全技术措施'}, {'title': '3.2.3 停电范围及操作边界'}],
                    'analysis': '已命中部分章节，但内容仍不完整。',
                    'reportExcerpt': '建议补齐作业内容边界。',
                },
            ],
            'sectionStructure': [
                {'id': 'section-11', 'title': '第11章 应急预案', 'level': 1, 'parentId': None},
            ],
        },
    }

    view_model = renderer.build_view_model(final_packet=packet, support_result=support_result)

    assert view_model.executiveSummaryView.verdict == '不通过'
    assert view_model.executiveSummaryView.metrics[0].label == '文档完整性'
    assert '监理工程师对停电施工方案的审核规则及要点' not in view_model.basisFiles
    assert '《危险性较大的分部分项工程专项施工方案编制指南》（建办质〔2021〕48号）' not in ''.join(view_model.basisFiles)
    assert '《中国南方电网公司电网建设工程专项施工方案管理工作指引》（2022）' in view_model.basisFiles
    assert '《电力安全工作规程 发电厂和变电站电气部分》GB 26860-2011' in view_model.basisFiles
    assert all('条文' not in item for item in view_model.basisFiles)
    assert view_model.chapterCompleteness.tableRows[1].matchedSection == '第3章、3.2.3'
    assert not getattr(view_model.chapterCompleteness, 'notes', [])
    assert view_model.normativeValidity.checks[0].statusLabel == '现行有效'
    html = renderer.render_html(view_model)
    css = renderer.render_print_css()
    assert '问题定位' in html
    assert '文档完整性矩阵' not in html
    assert '编制依据现行有效性核验' in html
    assert '相关审查意见' not in html
    assert 'structured-report__table-wrap--landscape' in html
    assert '@page wide' in css
    assert 'size: A4 portrait' in css
    assert '核验方式' not in html
    assert '说明' not in html
    assert '依据来源' not in html
    assert 'structured-report__issue-card--high' in html
    assert 'structured-report__issue-card--medium' in html
    assert '补充说明' not in html
    assert '**不通过**' not in html


def test_final_report_view_model_location_fallback_priority():
    renderer = FinalReportRenderer()
    packet = FinalReportPacket(
        review_id='r2',
        executive_summary='需要修改。',
        all_findings=[
            FindingItem(id='A', title='A', severity='high', summary='A', raw_data={'docEvidence': [{'excerpt': '第3章 3.1.2 计划停电工作时间'}]}),
            FindingItem(id='B', title='B', severity='high', summary='B', raw_data={'docEvidence': [{'locator': {'sectionId': 'section-11'}, 'excerpt': '演练要求未闭合'}]}),
            FindingItem(id='C', title='C', severity='high', summary='C', raw_data={}),
            FindingItem(id='D', title='D', severity='high', summary='D', raw_data={}),
        ],
    )
    support_result = {
        'summary': {'documentType': 'distribution_network_special_scheme'},
        'issues': [
            _support_issue('B', 'B', '第5章 施工班组配置'),
            _support_issue('C', 'C', '现场派工名单与表格不一致，需复核'),
            _support_issue('D', 'D', None),
        ],
        'matrices': {
            'structureCompleteness': [],
            'sectionStructure': [{'id': 'section-11', 'title': '第11章 应急预案', 'level': 1, 'parentId': None}],
        },
    }

    view_model = renderer.build_view_model(final_packet=packet, support_result=support_result)
    issue_map = {issue.id: issue for section in view_model.sections for issue in section.issues}

    assert issue_map['A'].location.startswith('第3章 3.1.2')
    assert issue_map['B'].location == '第11章'
    assert issue_map['C'].location.startswith('现场派工名单')
    assert issue_map['D'].location == '未定位到稳定章节，请结合原文复核。'


def test_final_report_view_model_filters_to_selected_modules_and_dedupes_near_duplicates():
    renderer = FinalReportRenderer()
    packet = FinalReportPacket(
        review_id='r3',
        executive_summary='本次审查已由专业主审组件裁决完成，总体评级结论为：**需要修改**。',
        all_findings=[
            FindingItem(
                id='S-1',
                title='停电施工作业专项章节不完整',
                severity='high',
                summary='第六章停电申请审批与用户告知流程缺失。',
                raw_data={'module_name': 'structure_completeness'},
            ),
            FindingItem(
                id='S-2',
                title='停电施工作业专项章节存在缺项',
                severity='high',
                summary='第六章停电申请审批与用户告知流程缺失，需补齐。',
                raw_data={'module_name': 'structure_completeness'},
            ),
            FindingItem(
                id='E-1',
                title='停送电链路闭环不足',
                severity='medium',
                summary='第5.1.5节派工闭环不足。',
                raw_data={'module_name': 'execution_continuity'},
            ),
            FindingItem(
                id='L-1',
                title='规范依据不完整',
                severity='medium',
                summary='依据缺失。',
                raw_data={'module_name': 'legality_compliance'},
            ),
        ],
        metadata={'selected_review_modules': ['structure_completeness', 'execution_continuity']},
    )

    view_model = renderer.build_view_model(
        final_packet=packet,
        support_result={'summary': {'documentType': 'distribution_network_special_scheme'}, 'issues': [], 'matrices': {}},
        selected_modules=['structure_completeness', 'execution_continuity'],
    )

    assert [section.key for section in view_model.sections] == ['structure_completeness', 'execution_continuity']
    assert len(view_model.sections[0].issues) == 1
    assert view_model.sections[0].issues[0].location.startswith('第六章')
    assert view_model.executiveSummaryView.metrics[0].label == '文档完整性'
    assert view_model.executiveSummaryView.metrics[1].label == '技术方案审查'


# ---------------------------------------------------------------------------
# Regression tests (2026-04-15)
# ---------------------------------------------------------------------------

def test_executive_summary_no_stats_sentence():
    """Executive summary must NOT contain '本次结果共覆盖' or issue count statistics."""
    renderer = FinalReportRenderer()
    packet = FinalReportPacket(
        review_id='r-stats',
        executive_summary='本次审查已由专业主审组件裁决完成，总体评级结论为：**需要修改**。',
        all_findings=[
            FindingItem(id='X-1', title='测试问题', severity='high', summary='测试',
                        raw_data={'module_name': 'legality_compliance'}),
        ],
    )
    view_model = renderer.build_view_model(
        final_packet=packet,
        support_result={'summary': {'documentType': 'construction_scheme'}, 'issues': [], 'matrices': {}},
    )
    assert '本次结果共覆盖' not in view_model.executiveSummary
    assert '形成' not in view_model.executiveSummary
    assert '项审查问题' not in view_model.executiveSummary
    html_output = renderer.render_html(view_model)
    assert '本次结果共覆盖' not in html_output


def test_legacy_executive_summary_with_stats_is_filtered_in_narrative():
    """Legacy data that still contains the stats sentence should be filtered out
    from the narrative view via defense-in-depth in _parse_executive_summary."""
    renderer = FinalReportRenderer()
    packet = FinalReportPacket(
        review_id='r-legacy',
        executive_summary=(
            '本次审查已由专业主审组件裁决完成，总体评级结论为：**不通过**。'
            ' 本次结果共覆盖 5 个审查模块（文档完整性、合规审查、依据与验证、内容一致性、技术方案审查），'
            '形成 103 项审查问题（高风险 48 项，中等风险 47 项，低风险 1 项）。'
        ),
        all_findings=[],
    )
    view_model = renderer.build_view_model(
        final_packet=packet,
        support_result={'summary': {}, 'issues': [], 'matrices': {}},
    )
    assert view_model.executiveSummaryView.verdict == '不通过'
    # The narrative must NOT contain the stats sentence.
    assert '本次结果共覆盖' not in view_model.executiveSummaryView.narrative


def test_normative_validity_unknown_shows_note():
    """Unknown normative validity items must carry a non-empty note."""
    renderer = FinalReportRenderer()
    packet = FinalReportPacket(
        review_id='r-nv-note',
        executive_summary='总体评级结论为：**需要修改**。',
        all_findings=[
            FindingItem(
                id='NV-1',
                title='编制依据现行有效性核验',
                severity='info',
                category='evidence_verification',
                raw_data={
                    'module_name': 'evidence_validation',
                    'normativeValidityChecks': [
                        {
                            'title': '《电线电缆识别标志方法》GB/T 6995',
                            'status': 'unknown',
                            'summary': '原文引用缺少年份或分册版本号，无法唯一映射到具体现行标准，需人工核验。',
                        },
                    ],
                },
            ),
        ],
    )
    view_model = renderer.build_view_model(
        final_packet=packet,
        support_result={'summary': {}, 'issues': [], 'matrices': {}},
    )
    assert len(view_model.normativeValidity.checks) == 1
    check = view_model.normativeValidity.checks[0]
    assert check.status == 'unknown'
    assert check.statusLabel == '待人工核验'
    assert '缺少年份' in check.note or '需人工核验' in check.note


def test_normative_validity_current_with_resolved_title():
    """When a bare standard is uniquely resolved, the display title and note should
    reflect the resolved versioned standard."""
    renderer = FinalReportRenderer()
    packet = FinalReportPacket(
        review_id='r-nv-resolved',
        executive_summary='总体评级结论为：**有条件通过**。',
        all_findings=[
            FindingItem(
                id='NV-2',
                title='编制依据现行有效性核验',
                severity='info',
                category='evidence_verification',
                raw_data={
                    'module_name': 'evidence_validation',
                    'normativeValidityChecks': [
                        {
                            'title': 'GB/T 50300',
                            'status': 'current',
                            'resolvedTitle': 'GB/T 50300-2013 建筑工程施工质量验收统一标准',
                        },
                    ],
                },
            ),
        ],
    )
    view_model = renderer.build_view_model(
        final_packet=packet,
        support_result={'summary': {}, 'issues': [], 'matrices': {}},
    )
    check = view_model.normativeValidity.checks[0]
    assert check.status == 'current'
    assert check.statusLabel == '现行有效'
    # Display title should be the resolved versioned title.
    assert 'GB/T 50300-2013' in check.title
    assert check.resolvedTitle == 'GB/T 50300-2013 建筑工程施工质量验收统一标准'
    assert '已确认现行标准' in check.note


# ---------------------------------------------------------------------------
# Regression tests (2026-04-15, batch 2): normative scope, note column, prose dedup
# ---------------------------------------------------------------------------

def test_normative_validity_note_in_status_column_not_title():
    """The note text must appear in the status column, NOT in the title column."""
    renderer = FinalReportRenderer()
    packet = FinalReportPacket(
        review_id='r-note-col',
        executive_summary='总体评级结论为：**需要修改**。',
        all_findings=[
            FindingItem(
                id='NV-COL',
                title='编制依据现行有效性核验',
                severity='info',
                category='evidence_verification',
                raw_data={
                    'module_name': 'evidence_validation',
                    'normativeValidityChecks': [
                        {
                            'title': '《电线电缆识别标志方法》GB/T 6995',
                            'status': 'unknown',
                            'summary': '原文引用缺少年份或分册版本号，无法唯一映射到具体现行标准，需人工核验。',
                        },
                    ],
                },
            ),
        ],
    )
    view_model = renderer.build_view_model(
        final_packet=packet,
        support_result={'summary': {}, 'issues': [], 'matrices': {}},
    )
    html_output = renderer.render_html(view_model)
    # The note must NOT be inside the title <td>.
    # Parse: find the row containing '电线电缆' — the second <td> (title) must NOT
    # contain the muted note; the third <td> (status) must contain it.
    import re as _re
    row_match = _re.search(r'<tr>.*?电线电缆.*?</tr>', html_output, _re.DOTALL)
    assert row_match, 'Could not find the normative validity row in HTML'
    row_html = row_match.group(0)
    tds = _re.findall(r'<td>(.*?)</td>', row_html, _re.DOTALL)
    assert len(tds) == 3
    title_td = tds[1]
    status_td = tds[2]
    # Title column must NOT contain the muted note
    assert 'structured-report__muted' not in title_td
    assert '缺少年份' not in title_td
    # Status column MUST contain the muted note
    assert 'structured-report__muted' in status_td
    assert '缺少年份' in status_td or '需人工核验' in status_td


def test_executive_summary_no_duplicate_verdict_prose():
    """When narrative is empty (verdict sentence filtered) and verdict badge exists,
    the HTML must NOT contain the verdict prose sentence."""
    renderer = FinalReportRenderer()
    packet = FinalReportPacket(
        review_id='r-dup',
        executive_summary='本次审查已由专业主审组件裁决完成，总体评级结论为：**不通过**。',
        all_findings=[
            FindingItem(id='X-1', title='测试问题', severity='high', summary='测试',
                        raw_data={'module_name': 'legality_compliance'}),
        ],
    )
    view_model = renderer.build_view_model(
        final_packet=packet,
        support_result={'summary': {'documentType': 'construction_scheme'}, 'issues': [], 'matrices': {}},
    )
    # Verdict must be extracted
    assert view_model.executiveSummaryView.verdict == '不通过'
    html_output = renderer.render_html(view_model)
    # The badge must exist
    assert 'structured-report__verdict-badge' in html_output
    # The prose sentence must NOT appear as visible text in a <p>
    assert '本次审查已由专业主审组件裁决完成' not in html_output


def test_normative_validity_law_excluded_from_checks():
    """Laws/regulations (e.g. 《建设工程安全生产管理条例》) must NOT appear in
    normativeValidityChecks after scope narrowing."""
    from src.review.hermes.normative_validity import NormativeValidityChecker
    checker = NormativeValidityChecker()
    # Test the gate directly
    assert checker._is_standard_normative('《建设工程安全生产管理条例》') is False
    assert checker._is_standard_normative('《中华人民共和国安全生产法》') is False
    assert checker._is_standard_normative('《电力安全事故应急处置和调查处理条例》') is False


def test_normative_validity_internal_rule_excluded():
    """Internal management documents without standard codes must be excluded."""
    from src.review.hermes.normative_validity import NormativeValidityChecker
    checker = NormativeValidityChecker()
    assert checker._is_standard_normative('《某公司安全生产管理制度》') is False
    assert checker._is_standard_normative('《关于加强施工现场管理的通知》') is False
    assert checker._is_standard_normative('《施工现场管理暂行规定》') is False


def test_normative_validity_enterprise_standard_with_code_retained():
    """Enterprise standards WITH standard codes (Q/CSG, Q/GDW) must be retained."""
    from src.review.hermes.normative_validity import NormativeValidityChecker
    checker = NormativeValidityChecker()
    assert checker._is_standard_normative('《中国南方电网有限责任公司电力安全工作规程》Q/CSG 510001-2015') is True
    assert checker._is_standard_normative('Q/GDW 11372-2015 国家电网公司应急物资储备定额') is True
    # A standard that happens to contain '规定' but has a code should still pass
    assert checker._is_standard_normative('GB/T 50328-2014 建设工程文件归档规范') is True


def test_normative_validity_parse_result_excludes_laws():
    """The extraction pipeline should skip laws that appear in 编制依据 section."""
    from src.review.hermes.normative_validity import NormativeValidityChecker
    checker = NormativeValidityChecker()
    parse_result = type(
        'ParseResult',
        (),
        {
            'sections': [
                {'id': 'section-1', 'title': '第一章 编制依据', 'parentId': None},
            ],
            'blocks': [
                {'type': 'heading', 'sectionId': 'section-1', 'text': '第一章 编制依据'},
                {'type': 'paragraph', 'sectionId': 'section-1', 'text': '1. \u300a\u5efa\u8bbe\u5de5\u7a0b\u5b89\u5168\u751f\u4ea7\u7ba1\u7406\u6761\u4f8b\u300b'},
                {'type': 'paragraph', 'sectionId': 'section-1', 'text': '2. \u300a\u4e2d\u534e\u4eba\u6c11\u5171\u548c\u56fd\u5b89\u5168\u751f\u4ea7\u6cd5\u300b'},
                {'type': 'paragraph', 'sectionId': 'section-1', 'text': '3. 《中国南方电网有限责任公司电力安全工作规程》Q/CSG 510001-2015'},
                {'type': 'paragraph', 'sectionId': 'section-1', 'text': '4. 《深圳电网工程安全文明施工标准（2019年版）》'},
            ],
        },
    )()
    sources = checker._extract_sources_from_parse_result(parse_result)
    titles = [item['title'] for item in sources]
    # Laws must be filtered out
    assert not any('条例' in t for t in titles)
    assert not any('安全生产法' in t for t in titles)
    # Standards must be retained
    assert any('Q/CSG' in t for t in titles)
    assert any('施工标准' in t for t in titles)


def test_calculation_reviewer_in_module_bindings():
    """calculation_review_reviewer must be registered in evidence_validation bindings."""
    from src.review.hermes.module_bindings import REVIEW_MODULE_BINDINGS
    binding = REVIEW_MODULE_BINDINGS['evidence_validation']
    assert 'calculation_review_reviewer' in binding.hermes_templates


# ---- Regression tests: evidence validation section stability ----

def test_normative_validity_table_appears_in_evidence_validation_html():
    """When normativeValidityChecks exist, the evidence_validation section MUST contain the table."""
    renderer = FinalReportRenderer()
    packet = FinalReportPacket(
        review_id='r-norm',
        executive_summary='',
        all_findings=[
            FindingItem(
                id='NORM-001',
                title='GB 50303-2015 \u73b0\u884c\u6709\u6548',
                severity='info',
                category='evidence_verification',
                summary='\u7f16\u5236\u4f9d\u636e\u73b0\u884c\u6709\u6548\u6027\u6838\u9a8c\u7ed3\u679c',
                raw_data={
                    'template_id': 'normative_validity_reviewer',
                    'module_name': 'evidence_validation',
                    'normativeValidityChecks': [
                        {'title': 'GB 50303-2015', 'status': 'current', 'summary': ''},
                        {'title': 'DL/T 5161.1-2013', 'status': 'superseded', 'summary': '\u5df2\u88ab\u66ff\u4ee3'},
                    ],
                },
            ),
        ],
    )
    vm = renderer.build_view_model(final_packet=packet)
    html_output = renderer.render_html(vm)
    # Table headers must be present
    assert '\u6838\u9a8c\u72b6\u6001' in html_output
    assert '\u89c4\u8303\u540d\u79f0' in html_output
    # Specific check titles must appear
    assert 'GB 50303-2015' in html_output
    assert 'DL/T 5161.1-2013' in html_output
    # Must be in evidence_validation section
    assert '依据与验证' in html_output


def test_calculation_finding_only_in_evidence_validation():
    """Calculation reviewer findings must appear ONLY in evidence_validation, not in other modules."""
    renderer = FinalReportRenderer()
    packet = FinalReportPacket(
        review_id='r-calc',
        executive_summary='',
        all_findings=[
            FindingItem(
                id='CALC-001',
                title='\u8350\u8f7d\u8ba1\u7b97\u516c\u5f0f\u9009\u578b\u4e0d\u5f53',
                severity='medium',
                category='evidence_verification',
                summary='\u516c\u5f0f\u9002\u7528\u6027\u5b58\u7591\u3002',
                raw_data={
                    'template_id': 'calculation_review_reviewer',
                    'module_name': 'evidence_validation',
                },
            ),
            FindingItem(
                id='LEG-001',
                title='\u65bd\u5de5\u65b9\u6848\u7f16\u5236\u4e3b\u4f53\u4e0d\u5408\u89c4',
                severity='high',
                category='compliance',
                summary='\u7f16\u5236\u4e3b\u4f53\u8d44\u8d28\u4e0d\u7b26\u5408\u8981\u6c42\u3002',
                raw_data={'module_name': 'legality_compliance'},
            ),
        ],
    )
    vm = renderer.build_view_model(final_packet=packet)
    # Find each section by key
    ev_section = next(s for s in vm.sections if s.key == 'evidence_validation')
    other_sections = [s for s in vm.sections if s.key != 'evidence_validation']
    # Calculation finding must be in evidence_validation
    assert any('\u8350\u8f7d\u8ba1\u7b97' in issue.title for issue in ev_section.issues)
    # Calculation finding must NOT be in any other section
    for section in other_sections:
        assert not any('\u8350\u8f7d\u8ba1\u7b97' in issue.title for issue in section.issues)


def test_normative_finding_does_not_leak_to_other_modules():
    """Normative validity findings (template_id=normative_validity_reviewer) must
    never appear in legality_compliance or other modules, even if the title
    contains keywords that would match other module heuristics."""
    renderer = FinalReportRenderer()
    packet = FinalReportPacket(
        review_id='r-leak',
        executive_summary='',
        all_findings=[
            FindingItem(
                id='NV-001',
                title='\u7f16\u5236\u4f9d\u636e\u5f15\u7528\u5df2\u5e9f\u6b62/\u8fc7\u671f\u4f01\u4e1a\u6807\u51c6',
                severity='medium',
                category='compliance',  # intentionally wrong category
                summary='\u5e9f\u6b62\u6807\u51c6\u5f15\u7528\u3002',
                raw_data={
                    'template_id': 'normative_validity_reviewer',
                    'module_name': 'legality_compliance',  # intentionally wrong
                },
            ),
        ],
    )
    vm = renderer.build_view_model(final_packet=packet)
    ev_section = next(s for s in vm.sections if s.key == 'evidence_validation')
    leg_section = next(s for s in vm.sections if s.key == 'legality_compliance')
    # Hard mapping must override both category and module_name
    assert any('\u5e9f\u6b62' in issue.title for issue in ev_section.issues)
    assert not any('\u5e9f\u6b62' in issue.title for issue in leg_section.issues)


def test_template_hard_module_overrides_keyword_guessing():
    """_resolve_module must use template_id hard mapping even when raw_data
    contains a conflicting module_name."""
    renderer = FinalReportRenderer()
    finding = {
        'id': 'F-1',
        'title': '\u53c2\u6570\u4e00\u81f4\u6027\u6838\u67e5',
        'severity': 'medium',
        'category': 'parameter_consistency',
        'raw_data': {
            'template_id': 'calculation_review_reviewer',
            'module_name': 'parameter_consistency',
        },
    }
    assert renderer._resolve_module(finding) == 'evidence_validation'


def test_power_outage_reviewer_no_evidence_validation_module():
    """power_outage_operation_chain_reviewer must NOT declare evidence_validation
    in its review_modules metadata."""
    import json
    import pathlib
    template_path = pathlib.Path(__file__).parent.parent / 'src' / 'review' / 'hermes' / 'templates' / 'power_outage_operation_chain_reviewer.json'
    with open(template_path) as f:
        template = json.load(f)
    review_modules = template.get('metadata', {}).get('review_modules', [])
    assert 'evidence_validation' not in review_modules


def test_evidence_validation_subsection_title_when_table_and_issues_coexist():
    """When both normative validity table and issue cards exist in evidence_validation,
    the issues must be wrapped in a subsection with heading."""
    renderer = FinalReportRenderer()
    packet = FinalReportPacket(
        review_id='r-sub',
        executive_summary='',
        all_findings=[
            FindingItem(
                id='NV-SUB-001',
                title='\u6838\u9a8c\u6982\u89c8',
                severity='info',
                category='evidence_verification',
                summary='',
                raw_data={
                    'template_id': 'normative_validity_reviewer',
                    'module_name': 'evidence_validation',
                    'normativeValidityChecks': [
                        {'title': 'GB 50150-2016', 'status': 'current', 'summary': ''},
                    ],
                },
            ),
            FindingItem(
                id='CALC-SUB-001',
                title='\u5b89\u5168\u7cfb\u6570\u53d6\u503c\u4f9d\u636e\u4e0d\u660e',
                severity='medium',
                category='evidence_verification',
                summary='\u672a\u6807\u6ce8\u53d6\u503c\u6765\u6e90\u3002',
                raw_data={
                    'template_id': 'calculation_review_reviewer',
                    'module_name': 'evidence_validation',
                },
            ),
        ],
    )
    vm = renderer.build_view_model(final_packet=packet)
    html_output = renderer.render_html(vm)
    # Subsection title for issues must appear when table also exists
    assert '\u5176\u4ed6\u8bc1\u636e\u9a8c\u8bc1\u95ee\u9898' in html_output
    # Both table and issue content must be present
    assert 'GB 50150-2016' in html_output
    assert '\u5b89\u5168\u7cfb\u6570' in html_output


def test_normative_validity_table_from_raw_findings_not_lost_by_dedup():
    """Normative validity checks must be extracted from raw findings (pre-dedup),
    not from deduplicated findings, so the table is never lost."""
    renderer = FinalReportRenderer()
    # Create two findings with same id/title (would be deduped) but only one has checks
    packet = FinalReportPacket(
        review_id='r-dedup',
        executive_summary='',
        all_findings=[
            FindingItem(
                id='DUP-001',
                title='\u7f16\u5236\u4f9d\u636e\u6838\u9a8c',
                severity='info',
                category='evidence_verification',
                summary='',
                raw_data={
                    'template_id': 'normative_validity_reviewer',
                    'module_name': 'evidence_validation',
                    'normativeValidityChecks': [
                        {'title': 'GB 50168-2018', 'status': 'current', 'summary': ''},
                    ],
                },
            ),
            FindingItem(
                id='DUP-001',
                title='\u7f16\u5236\u4f9d\u636e\u6838\u9a8c',
                severity='info',
                category='evidence_verification',
                summary='',
                raw_data={
                    'template_id': 'normative_validity_reviewer',
                    'module_name': 'evidence_validation',
                },
            ),
        ],
    )
    vm = renderer.build_view_model(final_packet=packet)
    # Even though dedup would keep only one finding, the table must be built from raw findings
    assert len(vm.normativeValidity.checks) >= 1
    assert any('GB 50168-2018' in c.title for c in vm.normativeValidity.checks)


# ---- Regression tests: execution plan / enabledAgents ----

def test_evidence_validation_module_template_ids_include_all_reviewers():
    """module_template_ids(['evidence_validation']) must include normative, calculation, and visibility reviewers."""
    from src.review.hermes.module_bindings import module_template_ids
    template_ids = module_template_ids(['evidence_validation'])
    assert 'normative_validity_reviewer' in template_ids
    assert 'calculation_review_reviewer' in template_ids
    assert 'visibility_gap_reviewer' in template_ids


def test_all_five_modules_produce_complete_template_set():
    """When all 5 modules are enabled, all expected reviewers must be in the template set."""
    from src.review.hermes.module_bindings import module_template_ids
    all_modules = [
        'structure_completeness',
        'parameter_consistency',
        'legality_compliance',
        'execution_continuity',
        'evidence_validation',
    ]
    template_ids = module_template_ids(all_modules)
    # evidence_validation reviewers must be present
    assert 'normative_validity_reviewer' in template_ids
    assert 'calculation_review_reviewer' in template_ids
    assert 'visibility_gap_reviewer' in template_ids
    # other core reviewers must also be present
    assert 'structure_completeness_reviewer' in template_ids
    assert 'policy_compliance_reviewer' in template_ids


# ---- Regression tests: calculation reviewer minimum visible output ----

def test_calculation_fallback_finding_renders_in_evidence_validation():
    """When calculation reviewer produces the fallback finding (no calculation content),
    it must appear in the evidence_validation section of the final report."""
    renderer = FinalReportRenderer()
    packet = FinalReportPacket(
        review_id='r-calc-fallback',
        executive_summary='',
        all_findings=[
            FindingItem(
                id='H-CALC-FALLBACK-001',
                title='\u8ba1\u7b97\u6838\u9a8c\uff1a\u672a\u89c1\u8ba1\u7b97\u4e66\u6216\u9a8c\u7b97\u8fc7\u7a0b',
                severity='info',
                category='evidence_verification',
                summary='\u88ab\u5ba1\u65b9\u6848\u4e2d\u672a\u8bc6\u522b\u5230\u8ba1\u7b97\u5f0f\u3001\u9a8c\u7b97\u8fc7\u7a0b\u6216\u53c2\u6570\u53d6\u503c\u4f9d\u636e\uff0c\u65e0\u6cd5\u5b8c\u6210\u8ba1\u7b97\u6838\u9a8c\u3002',
                raw_data={
                    'template_id': 'calculation_review_reviewer',
                    'module_name': 'evidence_validation',
                },
            ),
        ],
    )
    vm = renderer.build_view_model(final_packet=packet)
    ev_section = next(s for s in vm.sections if s.key == 'evidence_validation')
    # Fallback finding must be visible in evidence_validation
    assert any('\u8ba1\u7b97\u6838\u9a8c' in issue.title for issue in ev_section.issues)
    # Must NOT be in any other section
    other_sections = [s for s in vm.sections if s.key != 'evidence_validation']
    for section in other_sections:
        assert not any('\u8ba1\u7b97\u6838\u9a8c' in issue.title for issue in section.issues)
    # HTML must also contain the finding
    html_output = renderer.render_html(vm)
    assert '\u8ba1\u7b97\u6838\u9a8c' in html_output
    assert '依据与验证' in html_output


# ---- Regression tests: title keyword routing ----

def test_basis_superseded_finding_routes_to_evidence_validation_by_title_keyword():
    """A finding titled '编制依据引用已废止/过期企业标准' from structured_review_primary_worker
    (category=compliance) MUST be routed to evidence_validation, NOT legality_compliance."""
    renderer = FinalReportRenderer()
    packet = FinalReportPacket(
        review_id='r-keyword-route',
        executive_summary='',
        all_findings=[
            FindingItem(
                id='H-KW-001',
                title='\u7f16\u5236\u4f9d\u636e\u5f15\u7528\u5df2\u5e9f\u6b62/\u8fc7\u671f\u4f01\u4e1a\u6807\u51c6',
                severity='medium',
                category='compliance',
                summary='\u7f16\u5236\u4f9d\u636e\u4e2d\u5f15\u7528\u7684\u4f01\u4e1a\u6807\u51c6\u5df2\u88ab\u66ff\u4ee3',
                raw_data={
                    'template_id': 'structured_review_primary_worker',
                    'review_modules': ['legality_compliance'],
                },
            ),
            FindingItem(
                id='H-KW-002',
                title='\u7f16\u5236\u4f9d\u636e\u5f15\u7528\u7248\u672c\u6ede\u540e\u4e14\u4e0e\u6b63\u6587\u98ce\u9669\u6307\u5357\u7248\u672c\u51b2\u7a81',
                severity='medium',
                category='compliance',
                summary='\u89c4\u8303\u7248\u672c\u5f15\u7528\u6df7\u4e71',
                raw_data={
                    'template_id': 'structured_review_primary_worker',
                },
            ),
        ],
    )
    vm = renderer.build_view_model(final_packet=packet)
    # Both findings must be in evidence_validation
    ev_section = next(s for s in vm.sections if s.key == 'evidence_validation')
    ev_titles = [issue.title for issue in ev_section.issues]
    assert any('\u7f16\u5236\u4f9d\u636e' in t for t in ev_titles), f'Expected \u7f16\u5236\u4f9d\u636e in ev titles: {ev_titles}'
    assert any('\u7248\u672c\u6ede\u540e' in t or '\u7248\u672c\u51b2\u7a81' in t for t in ev_titles)
    # Must NOT appear in legality_compliance
    lc_section = next((s for s in vm.sections if s.key == 'legality_compliance'), None)
    if lc_section:
        lc_titles = [issue.title for issue in lc_section.issues]
        assert not any('\u7f16\u5236\u4f9d\u636e' in t for t in lc_titles), f'\u7f16\u5236\u4f9d\u636e leaked to legality_compliance: {lc_titles}'
