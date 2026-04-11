from __future__ import annotations

"""008 support/export report material rendering.

Generated PDFs remain export materials for the Hermes-controlled final result flow.
They do not define product-level final decision ownership.
"""

import asyncio
import html
from pathlib import Path

from md2pdf.core import md2pdf

_DEFAULT_PDF_CSS = ""


def _wrap_html_document(*, report_html: str, report_print_css: str, title: str | None = None) -> str:
    safe_title = html.escape(title or 'Structured Review Report')
    return (
        '<!doctype html>'
        '<html lang="zh-CN">'
        '<head>'
        '<meta charset="utf-8" />'
        '<meta name="viewport" content="width=device-width, initial-scale=1" />'
        f'<title>{safe_title}</title>'
        f'<style>{_DEFAULT_PDF_CSS}\n{report_print_css}</style>'
        '</head>'
        f'<body>{report_html}</body>'
        '</html>'
    )


async def _render_html_pdf_via_playwright(
    *,
    report_html: str,
    report_print_css: str,
    output_path: Path,
    title: str | None = None,
) -> Path:
    from playwright.async_api import Error as PlaywrightError
    from playwright.async_api import async_playwright

    output_path.parent.mkdir(parents=True, exist_ok=True)
    html_document = _wrap_html_document(
        report_html=report_html,
        report_print_css=report_print_css,
        title=title,
    )
    try:
        launch_kwargs = {
            'args': [
                '--no-sandbox', 
                '--disable-setuid-sandbox', 
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--no-zygote',
                '--single-process',
            ]
        }

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(**launch_kwargs)
            page = await browser.new_page()
            await page.set_content(html_document, wait_until='load')
            await page.emulate_media(media='print')
            await page.pdf(
                path=str(output_path),
                format='A4',
                landscape=True,
                print_background=True,
                prefer_css_page_size=True,
                display_header_footer=False,
            )
            await browser.close()
    except PlaywrightError as exc:  # pragma: no cover - exercised via fallback tests
        raise RuntimeError(f'playwright_browser_unavailable: {exc}') from exc
    return output_path


def _render_markdown_fallback_pdf(markdown_content: str, output_path: Path) -> Path:
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


async def render_structured_review_pdf(
    *,
    report_html: str,
    report_print_css: str,
    output_path: Path,
    title: str | None = None,
    markdown_fallback: str | None = None,
) -> Path:
    try:
        return await _render_html_pdf_via_playwright(
            report_html=report_html,
            report_print_css=report_print_css,
            output_path=output_path,
            title=title,
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"PLAYWRIGHT CRASHED! Falling back to md2pdf. Error: {e}")
        if markdown_fallback is None:
            raise
        return await asyncio.to_thread(_render_markdown_fallback_pdf, markdown_fallback, output_path)


def render_structured_review_pdf_sync(
    *,
    report_html: str,
    report_print_css: str,
    output_path: Path,
    title: str | None = None,
    markdown_fallback: str | None = None,
) -> Path:
    return asyncio.run(
        render_structured_review_pdf(
            report_html=report_html,
            report_print_css=report_print_css,
            output_path=output_path,
            title=title,
            markdown_fallback=markdown_fallback,
        )
    )
