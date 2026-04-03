from __future__ import annotations

import re
from typing import Any


_WEIGHT_RE = re.compile(r'Q计[^=]*=\s*([0-9]+(?:\.[0-9]+)?)t', re.IGNORECASE)
_CRANE_RE = re.compile(r'(?:选用|采用)\s*(\d+)T汽车吊', re.IGNORECASE)


_MEASURE_KEYWORDS = ['安全保证措施', '安全技术措施', '监测监控', '危险源', '风险辨识']


def extract_hazard_facts(parse_result) -> tuple[dict[str, Any], dict[str, list[str]], list[str]]:
    text = parse_result.normalizedText
    block_refs: dict[str, list[str]] = {
        'hazard.liftingOperation': [],
        'hazard.gasArea': [],
        'hazard.hotWork': [],
        'hazard.temporaryPower': [],
        'hazard.specialSchemePlanStatus': [],
        'hazard.craneCapacityTon': [],
        'hazard.calculatedLiftWeightTon': [],
        'hazard.highRiskCategories': [],
        'hazard.calculationEvidencePresent': [],
        'hazard.measureSectionPresent': [],
        'hazard.monitoringSectionPresent': [],
    }

    risk_categories: list[str] = []
    for block in parse_result.blocks:
        content = str(block.get('text') or '')
        if '汽车吊' in content or '吊装' in content:
            block_refs['hazard.liftingOperation'].append(block['id'])
        if '煤气区域' in content or '煤气' in content:
            block_refs['hazard.gasArea'].append(block['id'])
        if '动火' in content:
            block_refs['hazard.hotWork'].append(block['id'])
        if '施工用电' in content or '临时用电' in content or '停送电' in content:
            block_refs['hazard.temporaryPower'].append(block['id'])
        if '专项施工方案' in content:
            block_refs['hazard.specialSchemePlanStatus'].append(block['id'])
        if '起重吊装' in content and 'lifting_operations' not in risk_categories:
            risk_categories.append('lifting_operations')
            block_refs['hazard.highRiskCategories'].append(block['id'])
        if any(keyword in content for keyword in ['施工用电', '临时用电', '停送电']) and 'temporary_power' not in risk_categories:
            risk_categories.append('temporary_power')
            block_refs['hazard.highRiskCategories'].append(block['id'])
        if '动火作业' in content and 'hot_work' not in risk_categories:
            risk_categories.append('hot_work')
            block_refs['hazard.highRiskCategories'].append(block['id'])
        if '高处作业' in content and 'working_at_height' not in risk_categories:
            risk_categories.append('working_at_height')
            block_refs['hazard.highRiskCategories'].append(block['id'])
        if any(keyword in content for keyword in ['验算', '计算书', '受力计算']):
            block_refs['hazard.calculationEvidencePresent'].append(block['id'])
        if any(keyword in content for keyword in ['安全保证措施', '安全技术措施', '安全管理措施']):
            block_refs['hazard.measureSectionPresent'].append(block['id'])
        if any(keyword in content for keyword in ['监测监控', '监控监测']):
            block_refs['hazard.monitoringSectionPresent'].append(block['id'])

    crane_match = _CRANE_RE.search(text)
    weight_match = _WEIGHT_RE.search(text)
    if crane_match:
        for block in parse_result.blocks:
            if crane_match.group(0) in str(block.get('text') or ''):
                block_refs['hazard.craneCapacityTon'].append(block['id'])
                break
    if weight_match:
        for block in parse_result.blocks:
            if weight_match.group(0) in str(block.get('text') or ''):
                block_refs['hazard.calculatedLiftWeightTon'].append(block['id'])
                break

    dedicated_section = any('专项施工方案' in section['title'] and int(section.get('level', 99)) <= 2 for section in parse_result.sections)
    if dedicated_section:
        special_scheme_status = 'explicit_section'
    elif block_refs['hazard.specialSchemePlanStatus']:
        special_scheme_status = 'generic_mention_only'
    else:
        special_scheme_status = 'not_found'

    section_presence = parse_result.visibilityReport.get('sectionPresenceCache') or {}
    facts = {
        'liftingOperation': bool(block_refs['hazard.liftingOperation']),
        'gasArea': bool(block_refs['hazard.gasArea']),
        'hotWork': bool(block_refs['hazard.hotWork']),
        'temporaryPower': bool(block_refs['hazard.temporaryPower']),
        'highRiskCategories': risk_categories,
        'craneCapacityTon': int(crane_match.group(1)) if crane_match else None,
        'calculatedLiftWeightTon': float(weight_match.group(1)) if weight_match else None,
        'specialSchemePlanStatus': special_scheme_status,
        'calculationEvidencePresent': bool(block_refs['hazard.calculationEvidencePresent']) or bool(crane_match and weight_match),
        'measureSectionPresent': bool(block_refs['hazard.measureSectionPresent']),
        'monitoringSectionPresent': bool(block_refs['hazard.monitoringSectionPresent']),
        'measureKeywordCount': sum(1 for keyword in _MEASURE_KEYWORDS if keyword in text),
    }
    unresolved = []
    if facts['liftingOperation'] and not facts['craneCapacityTon']:
        unresolved.append('craneCapacityTon')
    if facts['liftingOperation'] and not facts['calculatedLiftWeightTon']:
        unresolved.append('calculatedLiftWeightTon')
    return facts, block_refs, unresolved
