from __future__ import annotations

from collections import defaultdict
import re
from typing import Any

from src.domain.models import AttachmentVisibility
from src.review.parser.normalizer import clean_text

ATTACHMENT_RE = re.compile(r'(附件|附录)\s*([A-Za-z一二三四五六七八九十百零〇0-9]+)')
_MISSING_MARKERS = ('未附', '缺失', '缺少', '暂缺', '后补')


def _token_to_id(token: str) -> str:
    return clean_text(token).replace(' ', '')


def build_attachment_index(
    blocks: list[dict[str, Any]],
    *,
    parser_limited: bool = False,
    file_type: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    references: dict[str, list[dict[str, Any]]] = defaultdict(list)
    titles: dict[str, list[dict[str, Any]]] = defaultdict(list)
    explicit_missing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    title_positions: list[tuple[int, str, dict[str, Any]]] = []

    for index, block in enumerate(blocks):
        text = clean_text(str(block.get('text') or ''))
        if not text:
            continue
        for match in ATTACHMENT_RE.finditer(text):
            attachment_id = _token_to_id(match.group(2))
            references[attachment_id].append(block)
            if any(marker in text for marker in _MISSING_MARKERS):
                explicit_missing[attachment_id].append(block)
            if text.startswith(f'{match.group(1)}{match.group(2)}'):
                titles[attachment_id].append(block)
                title_positions.append((index, attachment_id, block))

    title_positions.sort(key=lambda item: item[0])
    attachments: list[dict[str, Any]] = []
    for attachment_id in sorted(set(references) | set(titles)):
        title_block = titles.get(attachment_id, [None])[0]
        title = clean_text(str(title_block.get('text') if title_block else f'附件{attachment_id}'))
        visibility = AttachmentVisibility.referenced_only
        parse_state = AttachmentVisibility.referenced_only.value
        reason = 'reference_detected_without_attachment_body'

        if explicit_missing.get(attachment_id):
            visibility = AttachmentVisibility.missing
            parse_state = AttachmentVisibility.missing.value
            reason = 'explicit_missing_marker'
        elif title_block is not None:
            current_index = next((pos for pos, aid, _ in title_positions if aid == attachment_id), None)
            next_index = next((pos for pos, aid, _ in title_positions if pos > (current_index or -1)), len(blocks))
            content_blocks = [
                candidate
                for candidate in blocks[(current_index or 0) + 1 : next_index]
                if clean_text(str(candidate.get('text') or ''))
            ]
            if content_blocks:
                visibility = AttachmentVisibility.parsed
                parse_state = AttachmentVisibility.parsed.value
                reason = 'attachment_body_visible'
            elif parser_limited:
                visibility = AttachmentVisibility.unknown
                parse_state = AttachmentVisibility.unknown.value
                reason = 'title_detected_but_body_not_reliably_parsed'
            else:
                visibility = AttachmentVisibility.attachment_unparsed
                parse_state = AttachmentVisibility.attachment_unparsed.value
                reason = 'title_detected_without_attachment_body'
        elif parser_limited:
            visibility = AttachmentVisibility.unknown
            parse_state = AttachmentVisibility.unknown.value
            reason = 'reference_detected_in_limited_parser'

        manual_review_needed = visibility != AttachmentVisibility.parsed
        attachments.append(
            {
                'id': f'attachment-{attachment_id}',
                'attachmentNumber': attachment_id,
                'title': title,
                'visibility': visibility.value,
                'parseState': parse_state,
                'manualReviewNeeded': manual_review_needed,
                'reason': reason,
                'referenceBlockIds': [block['id'] for block in references.get(attachment_id, [])],
                'titleBlockId': title_block['id'] if title_block else None,
            }
        )

    reason_counts: dict[str, int] = defaultdict(int)
    for item in attachments:
        reason = item.get('reason')
        if reason:
            reason_counts[str(reason)] += 1

    visibility_report = {
        'parserLimited': parser_limited,
        'fileType': file_type,
        'attachmentCount': len(attachments),
        'counts': {
            AttachmentVisibility.parsed.value: sum(1 for item in attachments if item['visibility'] == AttachmentVisibility.parsed.value),
            AttachmentVisibility.attachment_unparsed.value: sum(1 for item in attachments if item['visibility'] == AttachmentVisibility.attachment_unparsed.value),
            AttachmentVisibility.referenced_only.value: sum(1 for item in attachments if item['visibility'] == AttachmentVisibility.referenced_only.value),
            AttachmentVisibility.missing.value: sum(1 for item in attachments if item['visibility'] == AttachmentVisibility.missing.value),
            AttachmentVisibility.unknown.value: sum(1 for item in attachments if item['visibility'] == AttachmentVisibility.unknown.value),
        },
        'reasonCounts': dict(reason_counts),
        'manualReviewNeeded': any(item['manualReviewNeeded'] for item in attachments),
    }
    return attachments, visibility_report
