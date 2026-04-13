import asyncio
from pathlib import Path
from src.review.report.pdf_exporter import render_structured_review_pdf_sync
try:
    render_structured_review_pdf_sync(
        report_html="<h1>Test</h1>",
        report_print_css="",
        output_path=Path("test_out.pdf")
    )
    print("Playwright success!")
except Exception as e:
    print("Playwright failed:", e)
