from __future__ import annotations

from pathlib import Path

from md2pdf.core import md2pdf


_DEFAULT_PDF_CSS = """
@page {
  size: A4;
  margin: 18mm 16mm 18mm 16mm;
}

body {
  font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
  font-size: 11pt;
  line-height: 1.7;
  color: #1f2937;
}

h1, h2, h3, h4 {
  color: #111827;
  page-break-after: avoid;
}

h1 {
  font-size: 20pt;
  margin: 0 0 10pt;
}

h2 {
  font-size: 15pt;
  margin: 18pt 0 8pt;
  padding-bottom: 4pt;
  border-bottom: 1px solid #d1d5db;
}

h3 {
  font-size: 12.5pt;
  margin: 14pt 0 6pt;
}

h4 {
  font-size: 11.5pt;
  margin: 10pt 0 4pt;
}

p, li {
  orphans: 2;
  widows: 2;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin: 10pt 0 14pt;
  font-size: 9.5pt;
}

th, td {
  border: 1px solid #cbd5e1;
  padding: 6pt 7pt;
  vertical-align: top;
}

th {
  background: #eef2f7;
  font-weight: 700;
}

code, pre {
  font-family: "SFMono-Regular", "Menlo", "Consolas", monospace;
}

blockquote {
  margin: 10pt 0;
  padding-left: 10pt;
  border-left: 3px solid #cbd5e1;
  color: #4b5563;
}
"""


def render_structured_review_pdf(markdown_content: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    css_path = output_path.with_suffix('.pdf.css')
    css_path.write_text(_DEFAULT_PDF_CSS, encoding='utf-8')
    try:
        md2pdf(
            pdf=output_path,
            raw=markdown_content,
            css=css_path,
            base_url=output_path.parent,
        )
    finally:
        css_path.unlink(missing_ok=True)
    return output_path
