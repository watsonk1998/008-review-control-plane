from __future__ import annotations

import re
from typing import Any


_SHUTDOWN_RE = re.compile(r'停机(?:改造)?时间为\s*(\d+)天')
_PLAN_TITLE_RE = re.compile(r'标题[:：]\s*(.+)')


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

    attachment_refs = [attachment['id'] for attachment in parse_result.attachments]
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
    if attachment_refs and not refs['schedule.attachmentRefs']:
        unresolved.append('attachmentRefs')
    return facts, refs, unresolved
