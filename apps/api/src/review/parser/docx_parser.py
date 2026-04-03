from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator

from docx import Document
from docx.document import Document as DocumentType
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph

from src.review.parser.attachment_indexer import build_attachment_index
from src.review.parser.normalizer import clean_text, detect_heading_level, normalize_lines, section_key


def _iter_block_items(document: DocumentType) -> Iterator[Paragraph | Table]:
    parent = document.element.body
    for child in parent.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, document)
        elif isinstance(child, CT_Tbl):
            yield Table(child, document)


def parse_docx_document(file_path: str | Path) -> dict[str, Any]:
    path = Path(file_path)
    document = Document(str(path))
    sections: list[dict[str, Any]] = []
    blocks: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    figures: list[dict[str, Any]] = []
    section_stack: list[dict[str, Any]] = []

    def current_section_id() -> str | None:
        return section_stack[-1]['id'] if section_stack else None

    for index, item in enumerate(_iter_block_items(document), start=1):
        if isinstance(item, Paragraph):
            text = clean_text(item.text)
            if not text:
                continue
            style_name = item.style.name if item.style is not None else ''
            heading_level = detect_heading_level(text, style_name)
            block_id = f'block-{len(blocks) + 1}'
            block_type = 'paragraph'
            if heading_level is not None:
                while section_stack and int(section_stack[-1]['level']) >= heading_level:
                    section_stack.pop()
                section = {
                    'id': f'section-{len(sections) + 1}',
                    'title': text,
                    'key': section_key(text),
                    'level': heading_level,
                    'parentId': current_section_id(),
                    'blockId': block_id,
                    'styleName': style_name,
                    'position': index,
                }
                sections.append(section)
                section_stack.append(section)
                block_type = 'heading'
            if text.startswith('图'):
                block_type = 'figure'
                figures.append(
                    {
                        'id': f'figure-{len(figures) + 1}',
                        'title': text,
                        'blockId': block_id,
                        'sectionId': current_section_id(),
                    }
                )
            blocks.append(
                {
                    'id': block_id,
                    'type': block_type,
                    'text': text,
                    'sectionId': current_section_id(),
                    'styleName': style_name,
                    'headingLevel': heading_level,
                    'position': index,
                }
            )
            continue

        rows: list[list[str]] = []
        for row in item.rows:
            rows.append([clean_text(cell.text) for cell in row.cells])
        table_id = f'table-{len(tables) + 1}'
        table_record = {
            'id': table_id,
            'rows': rows,
            'rowCount': len(rows),
            'columnCount': len(rows[0]) if rows else 0,
            'sectionId': current_section_id(),
            'position': index,
            'preview': '\n'.join(' | '.join(row) for row in rows[:5]),
        }
        tables.append(table_record)
        blocks.append(
            {
                'id': f'block-{len(blocks) + 1}',
                'type': 'table',
                'text': table_record['preview'],
                'sectionId': current_section_id(),
                'tableId': table_id,
                'position': index,
            }
        )

    attachments, visibility_report = build_attachment_index(blocks)
    normalized_text = '\n'.join(normalize_lines([block['text'] for block in blocks if block['type'] != 'figure']))
    title_counts: dict[str, int] = {}
    duplicate_titles: list[str] = []
    for section in sections:
        if int(section['level']) > 2 or not str(section['title']).startswith('第'):
            continue
        key = section['key']
        title_counts[key] = title_counts.get(key, 0) + 1
        if title_counts[key] == 2:
            duplicate_titles.append(key)
    visibility_report['duplicateSectionTitles'] = duplicate_titles

    return {
        'documentId': path.stem,
        'filePath': str(path),
        'fileType': path.suffix.lower().lstrip('.'),
        'sections': sections,
        'blocks': blocks,
        'tables': tables,
        'attachments': attachments,
        'figures': figures,
        'normalizedText': normalized_text,
        'preview': normalized_text[:4000],
        'visibilityReport': visibility_report,
        'parseWarnings': [],
    }
