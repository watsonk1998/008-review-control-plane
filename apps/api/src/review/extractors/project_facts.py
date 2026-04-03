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
    section_presence, section_presence_refs = _collect_section_presence(parse_result)

    facts = {
        'documentTypeHint': document_type_hint,
        'projectName': project_name,
        'projectCode': project_code,
        'location': location,
        'duplicateSections': duplicate_sections,
        'specialEquipmentMentioned': bool(special_equipment_blocks),
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
        **section_presence_refs,
    }
    unresolved = [
        key
        for key, value in [('projectName', project_name), ('projectCode', project_code)]
        if not value
    ]
    return facts, refs, unresolved
