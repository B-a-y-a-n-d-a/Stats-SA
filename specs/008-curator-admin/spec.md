# 008 - Curator-Admin UI

Branch: `feature/008-curator-admin`
Depends on: 001, 002, 009 (needs the `curator_admin` role)
Blocks: none
Docs reference: [docs/02-architecture.md](../../docs/02-architecture.md) Section 4, [docs/03-security-governance-compliance.md](../../docs/03-security-governance-compliance.md) Section 6, demo script step 5

## Specification

The only role that can change what the assistant is allowed to know.

1. `POST /api/curator/sources` — upload a PDF or paste a URL, set category and title, calls the ingestion service (002).
2. `GET /api/curator/sources` — list all sources with version/superseded status.
3. `DELETE /api/curator/sources/{id}` — retires a source (marks it non-retrievable, does not hard-delete, per audit requirements).
4. `GET|POST /api/curator/terminology` — list/create/version entries in the `terminology_guide` table ([docs/03-security-governance-compliance.md](../../docs/03-security-governance-compliance.md) Section 6.1 schema). For MVP, a Curator-Admin authors an entry; full dual-control (Communications Official approval) is deferred per [specs/000](../000-mvp-technical-decisions.md) — the schema fields for approval must exist, but the workflow enforcement is a roadmap item. State this clearly in the UI so it isn't presented as more governed than it is.
5. Frontend: source list + upload form, terminology list + add form.

Only the `curator_admin` role can call these endpoints — enforce server-side.

## Acceptance Criteria

- [x] Uploading a new PDF and triggering ingestion makes it queryable within the demo (matches demo script step 5 — "ask a question only that document can answer"). Verified live against the real Postgres container: uploaded the real `P0441_factsheetA.pdf` fixture as `curator_admin` via `POST /api/curator/sources`, then asked `POST /api/public/query` "How did GDP change in the manufacturing industry in Q2 2026?" (a fake LLM client that extracts the real retrieved chunk_id/quote stood in for the missing `LLM_API_KEY`, same pattern used for prior tasks) and got back `status: "answered"` with a real citation grounded in the uploaded document.
- [x] Re-uploading the same source creates a new version rather than overwriting. Verified live: re-uploading byte-identical content returned the same `source_id`/version 1 (no-op, per `ingestion/service.py`'s existing logic); re-uploading modified content under the same `url` returned a new `source_id`, `version: 2`, and `GET /api/curator/sources` showed the old row's `superseded_by` pointing at the new one.
- [x] Calling any `/api/curator/*` endpoint as a non-`curator_admin` user returns 403. Verified live for all 5 endpoints × 3 non-curator roles (public, media, comms_official) = 15 checks, all 403, using real seeded demo-account JWTs (not just `test_curator.py`'s in-memory-SQLite suite).
- [x] The terminology UI clearly labels entries as "not yet dual-approved" per the MVP scope note above. Verified live in a real browser against the running frontend + backend: the notice box renders under the Terminology Guide heading with the exact "not yet dual-approved" language; also drove the Sources upload-status table, the Terminology add-entry form, and the Retire button through real DOM interaction (confirmed via network-request inspection, not just component code) — an entry was added and correctly appeared as "Current", and retiring a source correctly flipped its badge to "Retired" and removed its Retire button.
- [x] **Additional, not in the original list — retiring the current version of a source makes it non-retrievable** (the harder, silent half of Criterion 3's "marks it non-retrievable"): verified live by retiring the just-uploaded (now-current) source and re-asking the exact same question — the response changed from `status: "answered"` with a citation to `status: "escalated"`, confirming `search.py`'s new `retired_at` filter actually removes it from what the assistant can cite, not just from the curator's own list view.

## Implementation Tasks

- [x] `backend/app/api/curator.py`
- [x] `backend/tests/test_curator.py`
- [x] `frontend/src/views/CuratorAdmin.tsx`
- [x] `frontend/src/api/curator.ts`
- [x] Update this file's checkboxes as you go, then open a PR into `master`

## Implementation notes

This task also touched files outside the original Implementation Tasks list above:

- `backend/app/db/models.py` gained `Source.retired_at` and `backend/alembic/versions/0002_source_retired_at.py` adds the matching column migration (applied live against the real Postgres container), because the schema had no way to represent "retired" (only `superseded_by`, which means versioning, not retirement) — both needed so `DELETE /api/curator/sources/{id}` can mark a source non-retrievable without hard-deleting it.
- `backend/app/retrieval/search.py` now also filters out `Source.retired_at IS NOT NULL`, since it's the only place chunks become retrievable and a retired source must stop being retrievable there (a hard acceptance criterion above, live-verified per the new criterion added).
- `backend/app/api/internal_ingest.py` was deleted (with its import and router registration removed from `backend/app/main.py`) because it exposed the same ingestion capability with no authentication at all, which became a real, live security hole once this properly-gated `/api/curator/sources` existed to replace it. Nothing else in the codebase called it over HTTP.
- `frontend/src/api/client.ts` — `apiFetch` unconditionally set `Content-Type: application/json`, which breaks a `FormData` body's multipart boundary. Fixed to only default that header when the body isn't `FormData`; every other existing caller is unaffected.
- **A real bug found only by live-testing the URL-paste ingestion path** (deliberately not covered by `test_curator.py` — it needs real network access): `POST /api/curator/sources` with no file attached fetches the PDF from `url` server-side via `httpx`. Tried against a real `statssa.gov.za` PDF URL and got a clean-looking `200 text/html` response — the site's bot-protection layer (Incapsula) returned a JS challenge page, not the PDF. That reached `pdfplumber` unvalidated and threw an unhandled `PdfminerException`, a raw 500 instead of a clean error. Fixed in `backend/app/api/curator.py` with a `file_bytes.startswith(b"%PDF-")` check before calling `ingest_source()`, returning `400 "The provided file is not a valid PDF."` instead. Covered by a new `test_curator.py` case (a directly-uploaded non-PDF file) and confirmed live twice more: the same real `statssa.gov.za` URL now returns a clean 400, and a second live check against a local HTTP server serving the real PDF fixture confirms the happy path (200, correctly ingested) still works.
