from __future__ import annotations

import re

_HEADING_PATTERNS: list[tuple[re.Pattern[str], int]] = [
    (re.compile(r'^第[一二三四五六七八九十百零〇0-9]+章'), 1),
    (re.compile(r'^第[一二三四五六七八九十百零〇0-9]+节'), 2),
    (re.compile(r'^(附录|附件)\s*[一二三四五六七八九十百零〇0-9]*'), 2),
    (re.compile(r'^[一二三四五六七八九十]+[、.]'), 3),
    (re.compile(r'^\d+(?:\.\d+){0,2}\s+'), 3),
    (re.compile(r'^\d+(?:\.\d+){1,4}'), 4),
]


def clean_text(text: str) -> str:
    value = text.replace('　', ' ').replace(' ', ' ')
    value = re.sub(r'\s+', ' ', value)
    return value.strip()


def normalize_lines(lines: list[str]) -> list[str]:
    normalized, _ = normalize_lines_with_metadata(lines)
    return normalized


def normalize_lines_with_metadata(lines: list[str]) -> tuple[list[str], dict[str, object]]:
    normalized: list[str] = []
    previous = None
    deduplicated_line_count = 0
    deduplicated_samples: list[str] = []
    for raw in lines:
        line = clean_text(raw)
        if not line:
            continue
        if previous == line:
            deduplicated_line_count += 1
            if len(deduplicated_samples) < 5:
                deduplicated_samples.append(line)
            continue
        normalized.append(line)
        previous = line
    return normalized, {
        'deduplicatedLineCount': deduplicated_line_count,
        'deduplicatedLineSamples': deduplicated_samples,
    }


def detect_heading_level(text: str, style_name: str | None = None) -> int | None:
    style = (style_name or '').lower()
    if 'heading 1' in style:
        return 1
    if 'heading 2' in style:
        return 2
    if 'heading 3' in style:
        return 3
    if 'heading 4' in style:
        return 4
    value = clean_text(text)
    for pattern, level in _HEADING_PATTERNS:
        if pattern.search(value):
            return level
    return None


def section_key(title: str) -> str:
    value = clean_text(title)
    value = re.sub(r'^第[一二三四五六七八九十百零〇0-9]+节\s*', '', value)
    value = re.sub(r'^第[一二三四五六七八九十百零〇0-9]+章\s*', '', value)
    value = re.sub(r'^附件\s*[一二三四五六七八九十百零〇0-9]+[:：]?\s*', '', value)
    return value or clean_text(title)
