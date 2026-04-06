from __future__ import annotations

from typing import Any

from src.review.parser.normalizer import section_key


def _find_block(blocks: list[dict[str, Any]], pattern: str) -> dict[str, Any] | None:
    for block in blocks:
        if pattern in str(block.get('text') or ''):
            return block
    return None


def _extract_value(blocks: list[dict[str, Any]], prefix: str) -> tuple[str | None, str | None]:
    block = _find_block(blocks, prefix)
    if block is None:
        return None, None
    text = str(block.get('text') or '')
    if '：' in text:
        return text.split('：', 1)[1].strip(), block['id']
    if ':' in text:
        return text.split(':', 1)[1].strip(), block['id']
    return text, block['id']


_DOC_TYPE_HINTS = {
    'hazardous_special_scheme': ['专项施工方案', '危大'],
    'construction_org': ['施工组织设计', '施工组织'],
    'construction_scheme': ['施工方案'],
    'supervision_plan': ['监理规划', '监理实施规划', '监理'],
}

_CONTEXT_ONLY_MARKERS = (
    '补充背景',
    '背景说明',
    '辅助材料',
    '支持材料',
    '不形成正式方案',
    '不作为正式方案',
    '仅供审查参考',
)

_SECTION_PRESENCE_LABELS = {
    'engineeringOverview': '工程概况',
    'preparationBasis': '编制依据',
    'constructionPlan': '施工部署/施工计划',
    'schedulePlan': '施工进度计划',
    'resourcePlan': '资源配置计划',
    'layoutPlan': '施工平面布置',
    'processMethod': '施工工艺/施工方法',
    'safetyMeasures': '安全措施',
    'emergencyPlan': '应急预案',
    'calculationBook': '计算书/验算',
    'monitoringPlan': '监测监控',
}

_WEAK_STRUCTURE_SECTION_KEYWORDS = (
    '工程概况',
    '工程简介',
    '编制依据',
    '编制说明',
    '施工计划',
    '施工部署',
    '施工进度计划',
    '进度计划',
    '工期安排',
    '资源配置',
    '资源配置计划',
    '劳动力计划',
    '机械设备计划',
    '施工总平面布置',
    '平面布置',
    '施工工艺',
    '工艺流程',
    '施工方法',
    '安全保证措施',
    '安全技术措施',
    '安全管理措施',
    '应急预案',
    '应急处置',
    '应急救援',
    '计算书',
    '验算',
    '受力计算',
    '监测监控',
    '监控监测',
)


def _infer_document_type_hint(text: str) -> str:
    for document_type, keywords in _DOC_TYPE_HINTS.items():
        if any(keyword in text for keyword in keywords):
            return document_type
    return 'review_support_material'


def _collect_section_presence(parse_result) -> tuple[dict[str, bool], dict[str, list[str]]]:
    presence = {
        'engineeringOverview': False,
        'preparationBasis': False,
        'constructionPlan': False,
        'schedulePlan': False,
        'resourcePlan': False,
        'layoutPlan': False,
        'processMethod': False,
        'safetyMeasures': False,
        'emergencyPlan': False,
        'calculationBook': False,
        'monitoringPlan': False,
    }
    refs = {f'project.sectionPresence.{key}': [] for key in presence}
    for section in parse_result.sections:
        title = str(section.get('title') or '')
        block_id = section.get('blockId')
        if any(keyword in title for keyword in ['工程概况', '工程简介']):
            presence['engineeringOverview'] = True
            if block_id:
                refs['project.sectionPresence.engineeringOverview'].append(block_id)
        if any(keyword in title for keyword in ['编制依据', '编制说明']):
            presence['preparationBasis'] = True
            if block_id:
                refs['project.sectionPresence.preparationBasis'].append(block_id)
        if any(keyword in title for keyword in ['施工计划', '施工部署']):
            presence['constructionPlan'] = True
            if block_id:
                refs['project.sectionPresence.constructionPlan'].append(block_id)
        if any(keyword in title for keyword in ['施工进度计划', '进度计划', '工期安排']):
            presence['schedulePlan'] = True
            if block_id:
                refs['project.sectionPresence.schedulePlan'].append(block_id)
        if any(keyword in title for keyword in ['资源配置', '资源配置计划', '劳动力计划', '机械设备计划']):
            presence['resourcePlan'] = True
            if block_id:
                refs['project.sectionPresence.resourcePlan'].append(block_id)
        if any(keyword in title for keyword in ['施工总平面布置', '平面布置']):
            presence['layoutPlan'] = True
            if block_id:
                refs['project.sectionPresence.layoutPlan'].append(block_id)
        if any(keyword in title for keyword in ['施工工艺', '工艺流程', '施工方法']):
            presence['processMethod'] = True
            if block_id:
                refs['project.sectionPresence.processMethod'].append(block_id)
        if any(keyword in title for keyword in ['安全保证措施', '安全技术措施', '安全管理措施']):
            presence['safetyMeasures'] = True
            if block_id:
                refs['project.sectionPresence.safetyMeasures'].append(block_id)
        if any(keyword in title for keyword in ['应急预案', '应急处置', '应急救援']):
            presence['emergencyPlan'] = True
            if block_id:
                refs['project.sectionPresence.emergencyPlan'].append(block_id)
        if any(keyword in title for keyword in ['计算书', '验算', '受力计算']):
            presence['calculationBook'] = True
            if block_id:
                refs['project.sectionPresence.calculationBook'].append(block_id)
        if any(keyword in title for keyword in ['监测监控', '监控监测']):
            presence['monitoringPlan'] = True
            if block_id:
                refs['project.sectionPresence.monitoringPlan'].append(block_id)
    return presence, refs


def _find_weak_section_structure_duplicates(parse_result) -> tuple[list[str], list[str]]:
    duplicates = {str(title) for title in parse_result.visibility.duplicateSectionTitles if title}
    if not duplicates:
        return [], []
    impacted_titles: list[str] = []
    impacted_refs: list[str] = []
    seen: set[str] = set()
    for section in parse_result.sections:
        title = str(section.get('title') or '')
        key = str(section.get('key') or section_key(title))
        if not title or not key or key not in duplicates:
            continue
        if int(section.get('level', 99)) > 2:
            continue
        if title.startswith(('附件', '附录')):
            if key not in seen:
                seen.add(key)
                impacted_titles.append(key)
            if section.get('blockId'):
                impacted_refs.append(str(section['blockId']))
            continue
        if title.startswith('第') and any(keyword in title for keyword in _WEAK_STRUCTURE_SECTION_KEYWORDS):
            if key not in seen:
                seen.add(key)
                impacted_titles.append(key)
            if section.get('blockId'):
                impacted_refs.append(str(section['blockId']))
    return impacted_titles, list(dict.fromkeys(impacted_refs))


def extract_project_facts(parse_result) -> tuple[dict[str, Any], dict[str, list[str]], list[str]]:
    blocks = parse_result.blocks
    project_name, project_name_ref = _extract_value(blocks, '项目名称')
    project_code, project_code_ref = _extract_value(blocks, '项目编号')
    location, location_ref = _extract_value(blocks, '施工地点')

    duplicate_map: dict[str, list[str]] = {}
    for section in parse_result.sections:
        if int(section.get('level', 99)) > 2 or not str(section.get('title', '')).startswith('第'):
            continue
        duplicate_map.setdefault(section_key(section['title']), []).append(section['blockId'])
    duplicate_sections = [title for title, refs in duplicate_map.items() if len(refs) > 1]

    document_type_hint = _infer_document_type_hint(parse_result.normalizedText[:3000])
    special_equipment_blocks = [block['id'] for block in blocks if '特种设备' in str(block.get('text') or '') or '行车' in str(block.get('text') or '')]
    context_only_blocks = [
        block['id']
        for block in blocks
        if any(marker in str(block.get('text') or '') for marker in _CONTEXT_ONLY_MARKERS)
    ]
    section_presence, section_presence_refs = _collect_section_presence(parse_result)
    weak_structure_duplicates, weak_structure_refs = _find_weak_section_structure_duplicates(parse_result)

    facts = {
        'documentTypeHint': document_type_hint,
        'projectName': project_name,
        'projectCode': project_code,
        'location': location,
        'duplicateSections': duplicate_sections,
        'specialEquipmentMentioned': bool(special_equipment_blocks),
        'contextOnly': bool(context_only_blocks),
        'sectionCount': len(parse_result.sections),
        'tableCount': len(parse_result.tables),
        'sectionPresence': section_presence,
    }
    refs = {
        'project.projectName': [project_name_ref] if project_name_ref else [],
        'project.projectCode': [project_code_ref] if project_code_ref else [],
        'project.location': [location_ref] if location_ref else [],
        'project.duplicateSections': [ref for title in duplicate_sections for ref in duplicate_map.get(title, [])],
        'project.specialEquipmentMentioned': special_equipment_blocks,
        'project.contextOnly': context_only_blocks,
        **section_presence_refs,
    }
    unresolved = []
    if weak_structure_duplicates:
        unresolved.append(
            {
                'code': 'weak_section_structure_signal',
                'factKey': 'project.duplicateSections',
                'summary': '关键章节或附件边界标题重复，canonical section extraction 不稳定，需人工复核章节归属。',
                'sourceExtractor': 'project_facts',
                'blockingReason': 'weak_section_structure_signal',
                'visibilityLimited': True,
            }
        )
    if not project_name:
        unresolved.append(
            {
                'code': 'missing_project_name',
                'factKey': 'project.projectName',
                'summary': '未解析到项目名称，需人工确认文档基础信息。',
                'sourceExtractor': 'project_facts',
                'blockingReason': 'parser_limited_source' if parse_result.parserLimited else 'missing_fact',
                'visibilityLimited': bool(parse_result.parserLimited),
            }
        )
    if not project_code:
        unresolved.append(
            {
                'code': 'missing_project_code',
                'factKey': 'project.projectCode',
                'summary': '未解析到项目编号，需人工确认文档标识信息。',
                'sourceExtractor': 'project_facts',
                'blockingReason': 'parser_limited_source' if parse_result.parserLimited else 'missing_fact',
                'visibilityLimited': bool(parse_result.parserLimited),
            }
        )
    if parse_result.parserLimited:
        for key, label in _SECTION_PRESENCE_LABELS.items():
            if section_presence.get(key):
                continue
            unresolved.append(
                {
                    'code': f'unresolved_section_presence_{key}',
                    'factKey': f'project.sectionPresence.{key}',
                    'summary': f'当前解析路径为 parser-limited，无法稳定确认“{label}”章节是否真实缺失。',
                    'sourceExtractor': 'project_facts',
                    'blockingReason': 'parser_limited_source',
                    'visibilityLimited': True,
                }
            )
    if weak_structure_refs:
        refs['project.duplicateSections'] = list(
            dict.fromkeys([*refs.get('project.duplicateSections', []), *weak_structure_refs])
        )
    return facts, refs, unresolved
