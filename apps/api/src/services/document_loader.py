from __future__ import annotations

from pathlib import Path

import docx2txt
import pdfplumber
from docx import Document

from src.review.parser.attachment_indexer import build_attachment_index
from src.review.parser.docx_parser import parse_docx_document
from src.review.parser.normalizer import clean_text, detect_heading_level, normalize_lines, section_key
from src.review.schema import DocumentParseResult


class DocumentLoader:
    def extract_text(self, file_path: str | Path) -> str:
        path = Path(file_path)
        suffix = path.suffix.lower()
        if suffix in {'.md', '.txt'}:
            return path.read_text(errors='ignore')
        if suffix == '.docx':
            text = docx2txt.process(str(path)) or ''
            if text.strip():
                return text
            document = Document(str(path))
            return '\n'.join(p.text for p in document.paragraphs)
        if suffix == '.pdf':
            parts: list[str] = []
            with pdfplumber.open(str(path)) as pdf:
                for page in pdf.pages:
                    parts.append(page.extract_text() or '')
            return '\n'.join(parts)
        raise ValueError(f'Unsupported document type: {path.suffix}')

    def parse_document(self, file_path: str | Path) -> DocumentParseResult:
        path = Path(file_path)
        suffix = path.suffix.lower()
        if suffix == '.docx':
            return DocumentParseResult.model_validate(parse_docx_document(path))
        if suffix in {'.md', '.txt', '.pdf'}:
            return DocumentParseResult.model_validate(self._parse_text_document(path, self.extract_text(path), markdown=suffix == '.md'))
        raise ValueError(f'Unsupported document type: {path.suffix}')

    def _parse_text_document(self, path: Path, text: str, *, markdown: bool) -> dict:
        lines = text.splitlines()
        sections: list[dict[str, object]] = []
        blocks: list[dict[str, object]] = []
        section_stack: list[dict[str, object]] = []
        figures: list[dict[str, object]] = []

        def current_section_id() -> str | None:
            return str(section_stack[-1]['id']) if section_stack else None

        for index, raw in enumerate(lines, start=1):
            if markdown and raw.lstrip().startswith('#'):
                hashes = len(raw) - len(raw.lstrip('#'))
                text_value = clean_text(raw.lstrip('#'))
                heading_level = min(max(hashes, 1), 4)
                style_name = f'Heading {heading_level}'
            else:
                text_value = clean_text(raw)
                style_name = ''
                heading_level = detect_heading_level(text_value)
            if not text_value:
                continue
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
                    'styleName': style_name,
                    'position': index,
                }
                sections.append(section)
                section_stack.append(section)
                block_type = 'heading'
            if text_value.startswith('图'):
                block_type = 'figure'
                figures.append({'id': f'figure-{len(figures) + 1}', 'title': text_value, 'blockId': block_id, 'sectionId': current_section_id()})
            blocks.append(
                {
                    'id': block_id,
                    'type': block_type,
                    'text': text_value,
                    'sectionId': current_section_id(),
                    'styleName': style_name,
                    'headingLevel': heading_level,
                    'position': index,
                }
            )

        attachments, visibility_report = build_attachment_index(blocks)
        normalized_text = '\n'.join(normalize_lines([str(block['text']) for block in blocks if block['type'] != 'figure']))
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
        return {
            'documentId': path.stem,
            'filePath': str(path),
            'fileType': path.suffix.lower().lstrip('.'),
            'sections': sections,
            'blocks': blocks,
            'tables': [],
            'attachments': attachments,
            'figures': figures,
            'normalizedText': normalized_text,
            'preview': normalized_text[:4000],
            'visibilityReport': visibility_report,
            'parseWarnings': [],
        }
