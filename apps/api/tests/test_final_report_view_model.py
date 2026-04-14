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


def test_final_report_view_model_builds_sections_and_chapter_notes():
    renderer = FinalReportRenderer()
    packet = FinalReportPacket(
        review_id='r1',
        executive_summary='总体评级：需要修改。',
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
                    'policyEvidence': [{'sourceId': 'construction-《危险性较大的分部分项工程专项施工方案编制指南》（建办质〔2021〕48号）', 'clauseTitle': '停电施工作业专项补充目录要求'}],
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
        ],
    )
    support_result = {
        'summary': {'documentType': 'distribution_network_special_scheme'},
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
                    'matchedSections': [{'title': '第3章 本次停电作业内容及安全技术措施'}],
                    'analysis': '已命中部分章节，但内容仍不完整。',
                    'reportExcerpt': '建议补齐作业内容边界。',
                },
            ]
        },
    }

    view_model = renderer.build_view_model(final_packet=packet, support_result=support_result)

    assert view_model.sections[0].title == '章节完整性'
    assert view_model.sections[1].title == '参数一致性'
    assert view_model.sections[2].title == '合法合规性'
    assert view_model.chapterCompleteness.tableRows[0].requirement == '停电范围'
    assert view_model.chapterCompleteness.notes
    assert view_model.sections[1].issues[0].location.startswith('3.1.2')
    assert view_model.sections[2].issues[0].location.startswith('第2章')
    html = renderer.render_html(view_model)
    assert '问题定位' in html
    assert '章节完整性矩阵' in html
    assert 'structured-report__issue-card--high' in html
    assert 'structured-report__issue-card--medium' in html


def test_final_report_view_model_location_fallback_priority():
    renderer = FinalReportRenderer()
    packet = FinalReportPacket(
        review_id='r2',
        executive_summary='需要修改。',
        all_findings=[
            FindingItem(id='A', title='A', severity='high', summary='A', raw_data={'docEvidence': [{'excerpt': '第3章 3.1.2 计划停电工作时间'}]}),
            FindingItem(id='B', title='B', severity='high', summary='B', raw_data={}),
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
        'matrices': {'structureCompleteness': []},
    }

    view_model = renderer.build_view_model(final_packet=packet, support_result=support_result)
    issue_map = {issue.id: issue for section in view_model.sections for issue in section.issues}

    assert issue_map['A'].location.startswith('第3章 3.1.2')
    assert issue_map['B'].location.startswith('第5章')
    assert issue_map['C'].location.startswith('现场派工名单')
    assert issue_map['D'].location == '未定位到稳定章节，请结合原文复核。'
