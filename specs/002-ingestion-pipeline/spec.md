# 002 - Ingestion Pipeline

Branch: `feature/002-ingestion-pipeline`
Depends on: 001 (data model must be merged first)
Blocks: 003 (retrieval needs chunks to search)
Docs reference: [docs/02-architecture.md](../../docs/02-architecture.md) Sections 1, 2, 4

## Specification

Turn an approved source document (PDF or URL) into rows in `sources` and `chunks`.

Pipeline steps:
1. Accept a PDF file upload or a URL to a Stats SA page.
2. Parse text and tables (layout-aware — statistical tables must not collapse into unreadable text, per Risk Register).
3. Chunk the parsed text (target ~300-500 tokens per chunk, preserve table rows intact within a single chunk where possible).
4. Compute a checksum of the raw source content (for change detection on re-ingestion).
5. Embed each chunk with `sentence-transformers/all-MiniLM-L6-v2` ([specs/000](../000-mvp-technical-decisions.md)).
6. Write one `sources` row and N `chunks` rows.
7. If a source with the same identity is re-ingested, create a new `version`, set `superseded_by` on the prior row, and re-embed rather than editing rows in place ([docs/02-architecture.md](../../docs/02-architecture.md) Section 4).

This task does NOT build the curator-admin UI (that is 008) — it exposes a Python function/service and a minimal internal API endpoint that 008 will call.

## Acceptance Criteria

- [x] `POST /internal/ingest` accepts a PDF upload or a URL + category + title, and returns the new `source_id`. Verified live: `curl -X POST .../internal/ingest -F file=@...` returned `200 {"source_id": "...", "version": 1}`.
- [x] A statistical table in a real Stats SA release PDF parses into readable chunk text, not garbled layout. Tested against a real GDP fact sheet (P0441, Q2 2026): 8 tables detected, rendered as clean pipe-delimited rows (e.g. industry-by-quarter growth rates), never split across chunks. Note: the GDP *press release* PDF turned out to be prose-only (references "Table 31" without embedding one) — the fact sheet was the real table-bearing document, which is itself a useful finding for curating the real 15-30 document set later.
- [x] Re-ingesting the same identity (same `url`) creates a new version and marks the old one `superseded_by`, never edits in place. Verified live: identical content re-ingested is a no-op (returns the existing row); modified content creates version 2, sets the old row's `superseded_by`, and both rows remain queryable.
- [x] A CLI script `backend/scripts/ingest_seed_set.py` bulk-ingests the curated document set from `seed_sources.yaml`. Verified live end-to-end against the real Postgres container.

**Bug found and fixed during live testing (not scoped to this task, but blocking it):** `backend/app/db/models.py`'s enum columns sent the Python enum *member name* (e.g. `"press_statement"`) instead of its *value* (`"Press Statement"`) to Postgres, which only accepts the values the migration defined. `UserRole` happened to have name == value, so Task 1's testing never caught it — inserting a `Source` row was the first thing to actually exercise a mismatched enum. Fixed with a `values_callable` wrapper applied to every enum column, not just the ones this task touches, so the same bug can't resurface elsewhere.

## Implementation Tasks

- [x] `backend/app/ingestion/parser.py` — PDF/table-aware text extraction (pdfplumber, not `unstructured` — see note below)
- [x] `backend/app/ingestion/chunker.py` — chunking logic
- [x] `backend/app/ingestion/embedder.py` — embedding wrapper
- [x] `backend/app/ingestion/service.py` — orchestrates parse -> chunk -> embed -> write, handles versioning
- [x] `backend/app/api/internal_ingest.py` — the internal endpoint
- [x] `backend/scripts/ingest_seed_set.py` + a `seed_sources.yaml` listing the curated documents (1 real entry so far; add more as the team curates the full 15-30)
- [x] Update this file's checkboxes as you go, then open a PR into `master`

**Deviation from specs/000's stack table:** swapped `unstructured` for `pdfplumber`. `unstructured`'s table-aware ("hi_res") strategy needs poppler/tesseract system binaries that aren't reliably available on Windows; `pdfplumber` is pure-Python, needs nothing extra, and its `extract_tables()` was sufficient to pass the table-readability acceptance criterion above against a real document.
