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
    assert view_model.executiveSummaryView.metrics[0].label == '章节完整性'
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
    assert '章节完整性矩阵' not in html
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
    assert view_model.executiveSummaryView.metrics[0].label == '章节完整性'
    assert view_model.executiveSummaryView.metrics[1].label == '工序连贯性'


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
            ' 本次结果共覆盖 5 个审查模块（章节完整性、合法合规性、证据验证、参数一致性、工序连贯性），'
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

