"""Unit tests for parsing/chunking against a real Stats SA PDF fixture (a GDP
fact sheet, chosen because it has both prose and real grid tables — a plain
press release turned out to be prose-only and reference tables without
embedding them). specs/002-ingestion-pipeline/spec.md. No DB or embedding
model needed here — those are covered by the live docker-compose run
documented in the PR."""
from pathlib import Path

from app.ingestion.chunker import chunk_text
from app.ingestion.parser import compute_checksum, parse_pdf

FIXTURE = Path(__file__).parent / "fixtures" / "P0441_factsheetA.pdf"


def _load():
    return FIXTURE.read_bytes()


def test_parse_pdf_extracts_all_pages():
    pages = parse_pdf(_load())
    assert len(pages) == 1
    assert all(p.text.strip() for p in pages)


def test_parse_pdf_renders_tables_readably():
    pages = parse_pdf(_load())
    combined = "\n".join(p.text for p in pages)
    assert "[Table]" in combined, "expected at least one detected table in the GDP fact sheet"
    assert "[/Table]" in combined


def test_checksum_is_deterministic():
    data = _load()
    assert compute_checksum(data) == compute_checksum(data)
    assert compute_checksum(data) != compute_checksum(data + b"x")


def test_chunk_text_keeps_tables_intact():
    pages = parse_pdf(_load())
    chunks = chunk_text(pages)
    assert len(chunks) > 0
    assert any("[Table]" in c["text"] for c in chunks), "expected at least one table-bearing chunk"
    for c in chunks:
        # A chunk containing a table start must also contain its end — never split.
        if "[Table]" in c["text"]:
            assert "[/Table]" in c["text"]
