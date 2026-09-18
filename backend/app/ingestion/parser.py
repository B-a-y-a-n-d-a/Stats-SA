# Implements specs/002-ingestion-pipeline/spec.md.
#
# PDF parsing must keep statistical tables readable, not collapse them into a
# jumble of digits (Risk Register: "PDF/table parsing errors on statistical
# tables and footnotes"). pdfplumber renders detected tables separately, as
# explicit pipe-delimited blocks, alongside the page's plain prose text.
import hashlib
from dataclasses import dataclass
from io import BytesIO

import pdfplumber


@dataclass
class ParsedPage:
    page_number: int
    text: str


def compute_checksum(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()


def _render_table(table: list[list[str | None]]) -> str:
    rows = [" | ".join((cell or "").strip() for cell in row) for row in table]
    return "[Table]\n" + "\n".join(rows) + "\n[/Table]"


def parse_pdf(file_bytes: bytes) -> list[ParsedPage]:
    pages: list[ParsedPage] = []
    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = (page.extract_text() or "").strip()
            tables = page.extract_tables()
            table_blocks = [_render_table(t) for t in tables if t]
            combined = "\n\n".join(filter(None, [text, *table_blocks]))
            pages.append(ParsedPage(page_number=i, text=combined))
    return pages
