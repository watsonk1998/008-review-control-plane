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
            '本次审查已由专业主审组件裁决完成，总体评级结论为：**不通过**。 '
            '底层设施提供事实抽提保障，当前命中 9 个预警指标（其中高危项 2 个，中阶 7 个，浅层瑕疵 0 个）。 '
            '经综合审阅与交叉校验，主审环节额外标注了 88 个需重点复核的深层风险点。'
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
    assert view_model.executiveSummaryView.metrics[0].value == '9 项'
    assert '监理工程师对停电施工方案的审核规则及要点' not in view_model.basisFiles
    assert '《危险性较大的分部分项工程专项施工方案编制指南》（建办质〔2021〕48号）' not in ''.join(view_model.basisFiles)
    assert '《中国南方电网公司电网建设工程专项施工方案管理工作指引》（2022）' in view_model.basisFiles
    assert '《电力安全工作规程 发电厂和变电站电气部分》GB 26860-2011' in view_model.basisFiles
    assert all('条文' not in item for item in view_model.basisFiles)
    assert view_model.chapterCompleteness.tableRows[1].matchedSection == '第3章、3.2.3'
    assert not getattr(view_model.chapterCompleteness, 'notes', [])
    assert view_model.normativeValidity.checks[0].statusLabel == '现行有效'
    html = renderer.render_html(view_model)
    assert '问题定位' in html
    assert '章节完整性矩阵' in html
    assert '编制依据现行有效性核验' in html
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
