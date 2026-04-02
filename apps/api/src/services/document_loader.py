from __future__ import annotations

from pathlib import Path
import docx2txt
import pdfplumber
from docx import Document


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
