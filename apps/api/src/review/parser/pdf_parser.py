from __future__ import annotations

from pathlib import Path
from typing import Any

import pdfplumber

from src.review.parser.attachment_indexer import build_attachment_index
from src.review.parser.normalizer import clean_text, detect_heading_level, normalize_lines_with_metadata, section_key


def parse_pdf_document(file_path: str | Path) -> dict[str, Any]:
    path = Path(file_path)
    sections: list[dict[str, Any]] = []
    blocks: list[dict[str, Any]] = []
    figures: list[dict[str, Any]] = []
    section_stack: list[dict[str, Any]] = []
    parse_warnings: list[str] = []

    page_count = 0
    extracted_page_count = 0

    def current_section_id() -> str | None:
        return str(section_stack[-1]['id']) if section_stack else None

    with pdfplumber.open(str(path)) as pdf:
        page_count = len(pdf.pages)
        for page_index, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text() or ''
            if page_text.strip():
                extracted_page_count += 1
            for line_index, raw in enumerate(page_text.splitlines(), start=1):
                text_value = clean_text(raw)
                if not text_value:
                    continue
                heading_level = detect_heading_level(text_value)
                block_id = f'block-{len(blocks) + 1}'
                block_type = 'paragraph'
                if heading_level is not None:
                    while section_stack and int(section_stack[-1]['level']) >= heading_level:
                        section_stack.pop()
                    section = {
                        'id': f'section-{len(sections) + 1}',
                        'title': text_value,
                        'key': section_key(text_value),
                        'level': heading_level,
                        'parentId': current_section_id(),
                        'blockId': block_id,
                        'styleName': f'PDF Heading {heading_level}',
                        'position': len(blocks) + 1,
                        'pageNumber': page_index,
                    }
                    sections.append(section)
                    section_stack.append(section)
                    block_type = 'heading'
                if text_value.startswith('图'):
                    block_type = 'figure'
                    figures.append(
                        {
                            'id': f'figure-{len(figures) + 1}',
                            'title': text_value,
                            'blockId': block_id,
                            'sectionId': current_section_id(),
                            'pageNumber': page_index,
                        }
                    )
                blocks.append(
                    {
                        'id': block_id,
                        'type': block_type,
                        'text': text_value,
                        'sectionId': current_section_id(),
                        'styleName': '',
                        'headingLevel': heading_level,
                        'position': len(blocks) + 1,
                        'pageNumber': page_index,
                        'lineNumber': line_index,
                    }
                )

    attachments, visibility_report = build_attachment_index(
        blocks,
        parser_limited=True,
        file_type=path.suffix.lower().lstrip('.'),
    )
    normalized_lines, normalization_meta = normalize_lines_with_metadata(
        [str(block['text']) for block in blocks if block['type'] != 'figure']
    )
    normalized_text = '\n'.join(normalized_lines)
    appendix_heading_candidates = [
        block
        for block in blocks
        if str(block.get('text') or '').startswith(('附件', '附录'))
    ]
    table_caption_candidates = [
        block
        for block in blocks
        if str(block.get('text') or '').startswith(('表', 'TABLE', 'Table'))
    ]
    figure_caption_candidates = [
        block
        for block in blocks
        if str(block.get('text') or '').startswith(('图', 'FIG', 'Figure'))
    ]
    title_counts: dict[str, int] = {}
    duplicate_titles: list[str] = []
    for section in sections:
        if int(section['level']) > 2:
            continue
        key = str(section['key'])
        title_counts[key] = title_counts.get(key, 0) + 1
        if title_counts[key] == 2:
            duplicate_titles.append(key)
    visibility_report['duplicateSectionTitles'] = duplicate_titles
    visibility_report['normalization'] = normalization_meta

    parse_warnings.extend(
        [
            'pdf_text_extraction_only',
            'pdf_tables_not_preserved',
            'pdf_attachment_visibility_may_be_unknown',
            'pdf_figures_images_not_parsed',
            f'pdf_appendix_title_candidates:{len(appendix_heading_candidates)}',
            f'pdf_table_caption_candidates:{len(table_caption_candidates)}',
            f'pdf_figure_caption_candidates:{len(figure_caption_candidates)}',
            f'pdf_source_pages:{page_count}',
            f'pdf_extracted_pages:{extracted_page_count}',
        ]
    )
    return {
        'documentId': path.stem,
        'filePath': str(path),
        'fileType': path.suffix.lower().lstrip('.'),
        'parseMode': 'pdf_text_only',
        'parserLimited': True,
        'sections': sections,
        'blocks': blocks,
        'tables': [],
        'attachments': attachments,
        'figures': figures,
        'normalizedText': normalized_text,
        'preview': normalized_text[:4000],
        'visibility': visibility_report,
        'visibilityReport': visibility_report,
        'parseWarnings': parse_warnings,
    }
