from __future__ import annotations

import re
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

    document_type_hint = 'construction_org' if '施工组织设计' in parse_result.normalizedText[:2000] else 'review_support_material'
    special_equipment_blocks = [block['id'] for block in blocks if '特种设备' in str(block.get('text') or '')]

    facts = {
        'documentTypeHint': document_type_hint,
        'projectName': project_name,
        'projectCode': project_code,
        'location': location,
        'duplicateSections': duplicate_sections,
        'specialEquipmentMentioned': bool(special_equipment_blocks),
        'sectionCount': len(parse_result.sections),
        'tableCount': len(parse_result.tables),
    }
    refs = {
        'project.projectName': [project_name_ref] if project_name_ref else [],
        'project.projectCode': [project_code_ref] if project_code_ref else [],
        'project.location': [location_ref] if location_ref else [],
        'project.duplicateSections': [ref for title in duplicate_sections for ref in duplicate_map.get(title, [])],
        'project.specialEquipmentMentioned': special_equipment_blocks,
    }
    unresolved = [
        key
        for key, value in [('projectName', project_name), ('projectCode', project_code), ('location', location)]
        if not value
    ]
    return facts, refs, unresolved
