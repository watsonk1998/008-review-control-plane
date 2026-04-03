from __future__ import annotations

import re
from typing import Any


_SHUTDOWN_RE = re.compile(r'停机(?:改造)?时间为\s*(\d+)天')
_PLAN_TITLE_RE = re.compile(r'标题[:：]\s*(.+)')
_EMERGENCY_SCENARIO_KEYWORDS = ('触电', '火灾', '起重', '吊装', '高处坠落', '机械伤害', '煤气', '中毒', '窒息')


def extract_schedule_resource_facts(parse_result) -> tuple[dict[str, Any], dict[str, list[str]], list[str]]:
    text = parse_result.normalizedText
    shutdown_match = _SHUTDOWN_RE.search(text)
    refs: dict[str, list[str]] = {
        'schedule.shutdownWindowDays': [],
        'resource.laborTotal': [],
        'resource.laborBreakdown': [],
        'schedule.attachmentRefs': [],
        'emergency.planTitles': [],
    }

    if shutdown_match:
        matched_text = shutdown_match.group(0)
        for block in parse_result.blocks:
            if matched_text in str(block.get('text') or ''):
                refs['schedule.shutdownWindowDays'].append(block['id'])
                break

    labor_total = None
    labor_breakdown: dict[str, int] = {}
    for table in parse_result.tables:
        rows = table.get('rows', [])
        if not rows:
            continue
        joined_header = ' '.join(rows[0]) + ' ' + (' '.join(rows[1]) if len(rows) > 1 else '')
        if '合计人数' not in joined_header:
            continue
        headers = rows[1] if len(rows) > 1 else rows[0]
        for row in rows[2:]:
            if len(row) < len(headers):
                continue
            maybe_total = row[-1]
            if maybe_total.isdigit():
                labor_total = int(maybe_total)
                for index, cell in enumerate(row[2:-1], start=2):
                    header = headers[index]
                    if cell.isdigit() and header:
                        labor_breakdown[header] = int(cell)
                refs['resource.laborTotal'].append(table['id'])
                refs['resource.laborBreakdown'].append(table['id'])
                break
        if labor_total is not None:
            break

    emergency_titles: list[str] = []
    for table in parse_result.tables:
        rows = table.get('rows', [])
        if len(rows) < 3:
            continue
        title_row = rows[2]
        joined = ' '.join(title_row)
        match = _PLAN_TITLE_RE.search(joined)
        if match:
            emergency_titles.append(match.group(1).strip())
            refs['emergency.planTitles'].append(table['id'])

    if not emergency_titles:
        seen_titles: set[str] = set()
        for block in parse_result.blocks:
            content = str(block.get('text') or '')
            if '应急预案' not in content:
                continue
            if not any(keyword in content for keyword in _EMERGENCY_SCENARIO_KEYWORDS):
                continue
            if content in seen_titles:
                continue
            seen_titles.add(content)
            emergency_titles.append(content[:80])
            refs['emergency.planTitles'].append(block['id'])

    attachment_refs = [attachment.id for attachment in parse_result.attachments]
    refs['schedule.attachmentRefs'] = attachment_refs.copy()

    facts = {
        'scheduleFacts': {
            'shutdownWindowDays': int(shutdown_match.group(1)) if shutdown_match else None,
            'attachmentRefs': attachment_refs,
        },
        'resourceFacts': {
            'laborTotal': labor_total,
            'laborBreakdown': labor_breakdown,
        },
        'emergencyFacts': {
            'planTitles': emergency_titles,
            'targetedPlanCount': len(emergency_titles),
        },
    }
    unresolved = []
    if not shutdown_match:
        unresolved.append(
            {
                'code': 'missing_shutdown_window_days',
                'factKey': 'schedule.shutdownWindowDays',
                'summary': '未解析到停机窗口时长，需人工确认工期窗口。',
            }
        )
    if labor_total is None:
        unresolved.append(
            {
                'code': 'missing_labor_total',
                'factKey': 'resource.laborTotal',
                'summary': '未解析到劳动力合计人数，需人工确认资源投入。',
            }
        )
    if not emergency_titles:
        unresolved.append(
            {
                'code': 'missing_emergency_plan_titles',
                'factKey': 'emergency.planTitles',
                'summary': '未解析到针对性应急预案标题，需人工确认应急安排。',
            }
        )
    return facts, refs, unresolved
