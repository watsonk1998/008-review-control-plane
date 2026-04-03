from __future__ import annotations

from collections import defaultdict
import re
from typing import Any

from src.domain.models import AttachmentVisibility
from src.review.parser.normalizer import clean_text

ATTACHMENT_RE = re.compile(r'附件\s*([一二三四五六七八九十百零〇0-9]+)')


def _token_to_id(token: str) -> str:
    return clean_text(token).replace(' ', '')


def build_attachment_index(blocks: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    references: dict[str, list[dict[str, Any]]] = defaultdict(list)
    titles: dict[str, list[dict[str, Any]]] = defaultdict(list)
    title_positions: list[tuple[int, str, dict[str, Any]]] = []

    for index, block in enumerate(blocks):
        text = clean_text(str(block.get('text') or ''))
        if not text:
            continue
        for match in ATTACHMENT_RE.finditer(text):
            attachment_id = _token_to_id(match.group(1))
            references[attachment_id].append(block)
            if text.startswith(f'附件{match.group(1)}'):
                titles[attachment_id].append(block)
                title_positions.append((index, attachment_id, block))

    title_positions.sort(key=lambda item: item[0])
    attachments: list[dict[str, Any]] = []
    for attachment_id in sorted(set(references) | set(titles)):
        title_block = titles.get(attachment_id, [None])[0]
        title = clean_text(str(title_block.get('text') if title_block else f'附件{attachment_id}'))
        visibility = AttachmentVisibility.referenced_only
        parse_state = 'referenced_only'
        if title_block is not None:
            visibility = AttachmentVisibility.attachment_unparsed
            parse_state = 'attachment_unparsed'
            current_index = next((pos for pos, aid, _ in title_positions if aid == attachment_id), None)
            next_index = next((pos for pos, aid, _ in title_positions if pos > (current_index or -1)), len(blocks))
            content_blocks = [
                candidate
                for candidate in blocks[(current_index or 0) + 1 : next_index]
                if clean_text(str(candidate.get('text') or ''))
            ]
            if content_blocks:
                visibility = AttachmentVisibility.parsed
                parse_state = 'parsed'
        attachments.append(
            {
                'id': f'attachment-{attachment_id}',
                'attachmentNumber': attachment_id,
                'title': title,
                'visibility': visibility.value,
                'parseState': parse_state,
                'referenceBlockIds': [block['id'] for block in references.get(attachment_id, [])],
                'titleBlockId': title_block['id'] if title_block else None,
            }
        )

    visibility_report = {
        'attachmentCount': len(attachments),
        'counts': {
            AttachmentVisibility.parsed.value: sum(1 for item in attachments if item['visibility'] == AttachmentVisibility.parsed.value),
            AttachmentVisibility.attachment_unparsed.value: sum(1 for item in attachments if item['visibility'] == AttachmentVisibility.attachment_unparsed.value),
            AttachmentVisibility.referenced_only.value: sum(1 for item in attachments if item['visibility'] == AttachmentVisibility.referenced_only.value),
            AttachmentVisibility.missing.value: 0,
            AttachmentVisibility.unknown.value: 0,
        },
        'manualReviewNeeded': any(item['visibility'] != AttachmentVisibility.parsed.value for item in attachments),
    }
    return attachments, visibility_report
