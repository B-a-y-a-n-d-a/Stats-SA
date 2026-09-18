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

- [ ] `POST /internal/ingest` accepts a PDF upload or a URL + category + title, and returns the new `source_id`.
- [ ] A statistical table in a real Stats SA release PDF (test with one QLFS or CPI release) parses into readable chunk text, not garbled layout.
- [ ] Re-ingesting the same `source_id`'s identity creates a new version and marks the old one `superseded_by`, never edits in place.
- [ ] A CLI script `backend/scripts/ingest_seed_set.py` bulk-ingests the initial 15-30 curated documents from a config list.

## Implementation Tasks

- [ ] `backend/app/ingestion/parser.py` — PDF/table-aware text extraction
- [ ] `backend/app/ingestion/chunker.py` — chunking logic
- [ ] `backend/app/ingestion/embedder.py` — embedding wrapper
- [ ] `backend/app/ingestion/service.py` — orchestrates parse -> chunk -> embed -> write, handles versioning
- [ ] `backend/app/api/internal_ingest.py` — the internal endpoint
- [ ] `backend/scripts/ingest_seed_set.py` + a `seed_sources.yaml` listing the curated 15-30 documents
- [ ] Update this file's checkboxes as you go, then open a PR into `master`
