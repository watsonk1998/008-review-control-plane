from __future__ import annotations

from typing import Any


_CONSTRUCTION_ORG_STRUCTURE_ITEMS: tuple[dict[str, Any], ...] = (
    {
        'itemKey': 'preparationBasis',
        'requirementLabel': '编制依据',
        'basisClause': '3.0.4',
        'basisRequirement': '施工组织设计应包括编制依据。',
        'primaryKeywords': ('编制依据', '编制说明'),
        'secondaryKeywords': (),
    },
    {
        'itemKey': 'engineeringOverview',
        'requirementLabel': '工程概况',
        'basisClause': '3.0.4、5.1',
        'basisRequirement': '施工组织设计应包括工程概况，并说明工程主要情况、设计简介和施工条件。',
        'primaryKeywords': ('工程概况', '工程简介'),
        'secondaryKeywords': ('工程主要情况',),
    },
    {
        'itemKey': 'constructionDeployment',
        'requirementLabel': '施工部署',
        'basisClause': '3.0.4、5.2',
        'basisRequirement': '施工组织设计应包括施工部署，并明确施工目标、施工顺序和总体安排。',
        'primaryKeywords': ('施工部署', '施工总部署', '施工安排'),
        'secondaryKeywords': ('施工阶段', '部署'),
    },
    {
        'itemKey': 'schedulePlan',
        'requirementLabel': '施工进度计划',
        'basisClause': '3.0.4、5.3',
        'basisRequirement': '施工组织设计应包括施工进度计划，并按施工部署编制。',
        'primaryKeywords': ('施工进度计划', '进度管理计划'),
        'secondaryKeywords': ('施工网络进度表', '网络进度表', '工期安排'),
    },
    {
        'itemKey': 'resourcePlan',
        'requirementLabel': '施工准备与资源配置计划',
        'basisClause': '3.0.4、5.4',
        'basisRequirement': '施工组织设计应包括施工准备与资源配置计划，覆盖技术准备、现场准备、资金准备及资源配置。',
        'primaryKeywords': ('施工准备与资源配置计划', '资源配置计划', '资源管理计划'),
        'secondaryKeywords': ('施工准备', '施工劳动力安排', '劳动力安排', '机械设备计划', '机械设备', '劳动力计划'),
    },
    {
        'itemKey': 'processMethod',
        'requirementLabel': '主要施工方案',
        'basisClause': '3.0.4、5.5',
        'basisRequirement': '施工组织设计应包括主要施工方案，对主要分部、分项工程及专项工程作出安排。',
        'primaryKeywords': ('主要施工方案', '施工方案'),
        'secondaryKeywords': ('施工方法', '施工工艺', '工艺流程'),
    },
    {
        'itemKey': 'layoutPlan',
        'requirementLabel': '施工现场平面布置',
        'basisClause': '3.0.4、5.6',
        'basisRequirement': '施工组织设计应包括施工现场平面布置，并结合不同施工阶段进行绘制或说明。',
        'primaryKeywords': ('施工现场平面布置', '施工总平面布置', '施工平面布置', '施工平面管理计划'),
        'secondaryKeywords': ('平面布置',),
    },
    {
        'itemKey': 'progressManagementPlan',
        'requirementLabel': '进度管理计划',
        'basisClause': '7.1.1、7.2',
        'basisRequirement': '主要施工管理计划应包括进度管理计划，并明确分解目标、职责及控制措施。',
        'primaryKeywords': ('进度管理计划',),
        'secondaryKeywords': ('施工进度计划', '施工网络进度表', '网络进度表'),
    },
    {
        'itemKey': 'qualityManagementPlan',
        'requirementLabel': '质量管理计划',
        'basisClause': '7.1.1、7.3',
        'basisRequirement': '主要施工管理计划应包括质量管理计划，并明确质量目标、组织职责和保障措施。',
        'primaryKeywords': ('质量管理计划',),
        'secondaryKeywords': ('质量控制措施', '质量保证措施', '质量管理目标'),
    },
    {
        'itemKey': 'safetyManagementPlan',
        'requirementLabel': '安全管理计划',
        'basisClause': '7.1.1、7.4',
        'basisRequirement': '主要施工管理计划应包括安全管理计划，并明确危险源、组织职责、控制措施和应急安排。',
        'primaryKeywords': ('安全管理计划',),
        'secondaryKeywords': ('安全保证措施', '安全管理措施', '专项安全措施', '施工用电安全'),
    },
    {
        'itemKey': 'environmentManagementPlan',
        'requirementLabel': '环境管理计划',
        'basisClause': '7.1.1、7.5',
        'basisRequirement': '主要施工管理计划应包括环境管理计划，并明确环境目标、组织职责和控制措施。',
        'primaryKeywords': ('环境管理计划',),
        'secondaryKeywords': ('文明施工措施', '环境因素控制措施'),
    },
    {
        'itemKey': 'costManagementPlan',
        'requirementLabel': '成本管理计划',
        'basisClause': '7.1.1、7.6.1~7.6.2',
        'basisRequirement': '主要施工管理计划应包括成本管理计划，并以施工预算和施工进度计划为依据编制。',
        'primaryKeywords': ('成本管理计划',),
        'secondaryKeywords': ('成本控制', '成本目标', '成本预算', '成本核算'),
    },
)


def _section_match_score(title: str, *, primary_keywords: tuple[str, ...], secondary_keywords: tuple[str, ...]) -> tuple[int, str | None]:
    for keyword in primary_keywords:
        if keyword and keyword in title:
            return 2, keyword
    for keyword in secondary_keywords:
        if keyword and keyword in title:
            return 1, keyword
    return 0, None


def _select_matches(
    sections: list[dict[str, Any]],
    *,
    primary_keywords: tuple[str, ...],
    secondary_keywords: tuple[str, ...],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    primary: list[dict[str, Any]] = []
    secondary: list[dict[str, Any]] = []
    for section in sections:
        title = str(section.get('title') or '')
        if not title:
            continue
        level = int(section.get('level', 99) or 99)
        if level > 3:
            continue
        score, matched_keyword = _section_match_score(
            title,
            primary_keywords=primary_keywords,
            secondary_keywords=secondary_keywords,
        )
        if score == 0:
            continue
        section_copy = {
            'sectionId': section.get('id'),
            'blockId': section.get('blockId'),
            'title': title,
            'position': section.get('position'),
            'level': level,
            'matchedKeyword': matched_keyword,
        }
        if score == 2 and level <= 2:
            primary.append(section_copy)
        else:
            secondary.append(section_copy)
    primary.sort(key=lambda item: (item.get('level', 99), item.get('position', 10**9), item['title']))
    secondary.sort(key=lambda item: (item.get('level', 99), item.get('position', 10**9), item['title']))
    return primary[:3], secondary[:3]


def _report_excerpt(label: str, status: str, matches: list[dict[str, Any]]) -> str:
    matched_titles = '、'.join(item['title'] for item in matches[:2])
    if status == 'matched':
        return f'已识别到“{matched_titles}”等章节，可支撑“{label}”结构审查。'
    if status == 'partial':
        return f'仅识别到“{matched_titles}”等局部章节，对“{label}”的支撑仍不完整。'
    if status == 'blocked_by_visibility':
        return f'当前解析受限，未能稳定确认“{label}”是否完整存在，需结合原件人工复核。'
    return f'当前未识别到可稳定对应“{label}”的章节。'


def _analysis_text(label: str, status: str, matches: list[dict[str, Any]], *, parser_limited: bool) -> str:
    matched_titles = '、'.join(item['title'] for item in matches[:3])
    if status == 'matched':
        return f'命中章节：{matched_titles}。'
    if status == 'partial':
        return f'仅命中局部相关章节：{matched_titles}；建议补齐或单列“{label}”。'
    if status == 'blocked_by_visibility':
        reason = '当前为受限解析路径' if parser_limited else '章节信号不足'
        return f'{reason}，尚不能稳定判断“{label}”是否真实缺失。'
    return f'当前正文中未识别到可稳定映射“{label}”的章节标题。'


def build_construction_org_structure_matrix(parse_result) -> tuple[list[dict[str, Any]], dict[str, list[str]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    refs: dict[str, list[str]] = {}
    unresolved: list[dict[str, Any]] = []
    parser_limited = bool(parse_result.parserLimited)
    for spec in _CONSTRUCTION_ORG_STRUCTURE_ITEMS:
        primary_matches, secondary_matches = _select_matches(
            parse_result.sections,
            primary_keywords=spec['primaryKeywords'],
            secondary_keywords=spec['secondaryKeywords'],
        )
        matched_sections = primary_matches or secondary_matches
        if primary_matches:
            status = 'matched'
        elif secondary_matches:
            status = 'partial'
        elif parser_limited:
            status = 'blocked_by_visibility'
        else:
            status = 'missing'
        fact_key = f'project.structureCompleteness.{spec["itemKey"]}'
        refs[fact_key] = [str(item['blockId']) for item in matched_sections if item.get('blockId')]
        if parser_limited and status != 'matched':
            unresolved.append(
                {
                    'code': f'unresolved_structure_completeness_{spec["itemKey"]}',
                    'factKey': fact_key,
                    'summary': f'当前解析路径受限，无法稳定确认“{spec["requirementLabel"]}”是否真实缺失。',
                    'sourceExtractor': 'project_facts',
                    'blockingReason': 'parser_limited_source',
                    'visibilityLimited': True,
                }
            )
        rows.append(
            {
                'itemKey': spec['itemKey'],
                'requirementLabel': spec['requirementLabel'],
                'basisClause': spec['basisClause'],
                'basisRequirement': spec['basisRequirement'],
                'status': status,
                'matchedSections': [
                    {
                        'sectionId': item.get('sectionId'),
                        'blockId': item.get('blockId'),
                        'title': item['title'],
                        'position': item.get('position'),
                        'level': item.get('level'),
                    }
                    for item in matched_sections
                ],
                'analysis': _analysis_text(
                    spec['requirementLabel'],
                    status,
                    matched_sections,
                    parser_limited=parser_limited,
                ),
                'reportExcerpt': _report_excerpt(spec['requirementLabel'], status, matched_sections),
            }
        )
    return rows, refs, unresolved
