# 007 - Communication Memory &amp; Response Reuse

Branch: `feature/007-communication-memory`
Depends on: 001, 003, 006 (reads approved reviews to populate memory)
Blocks: none
Docs reference: [docs/01-requirements-traceability.md](../../docs/01-requirements-traceability.md) Mandatory Functional Capability 6, demo script step 4

## Specification

1. When a draft is approved in the Review Console (006), write a row to `communication_memory`: `{query_text, final_answer, citations, approved_by, approved_at}`.
2. On every new query (public or media), search `communication_memory` for the closest matching prior approved response (keyword search is enough for MVP — semantic clustering is explicitly deferred per [docs/05-mvp-scope-and-roadmap.md](../../docs/05-mvp-scope-and-roadmap.md)).
3. Surface the best match (with a similarity/relevance score) alongside the draft in the Review Console, as supplementary context for the official — never auto-substitute it for a fresh draft.
4. Expose `GET /api/memory/search?q=` for the Curator-Admin or Communications Official to search the repository directly by keyword.

## Acceptance Criteria

- [x] Approving a draft in 006 creates a `communication_memory` row automatically. Verified live against real Postgres: approving a media draft wrote a real row, confirmed via `GET /api/memory/search`.
- [x] Submitting a second, related media query surfaces the just-approved response as a suggested reuse match with a visible score (matches demo script step 4). Verified live, replaying the exact scenario: approved "How did GDP change in manufacturing in Q2 2026?", then submitted "What happened to GDP in the manufacturing sector this quarter?" — the queue correctly surfaced the first as a reuse match with score 0.3. A third, unrelated query ("best recipe for chocolate cake") correctly showed no match.
- [x] `/api/memory/search` returns keyword-relevant results ranked by relevance. Verified live; also verified role gating (403 for public, 200 for curator_admin/comms_official) and 400 on a missing `q`.

**Reused, didn't duplicate:** the two backend/frontend agents that built this in parallel each wrote their own copy of the match-serializing helper (one in `review.py`, one in `memory.py`) — consolidated by hand into a single `memory_match.serialize_match` both routers import, so there is exactly one place that shape is defined.

**A real, necessary fix to specs/006's own merged test suite:** `POST /api/review/{draft_id}/decide` now unconditionally writes to `communication_memory` on approve/edit_approve, which broke `test_review.py`'s in-memory SQLite setup (it only created `queries`/`drafts`/`reviews`/`audit_log`) — every approve/edit_approve/queue test in that file started failing with "no such table: communication_memory" until `communication_memory` was added to its table-creation list. Unavoidable and correct: specs/006 predates specs/007, but the two are now genuinely coupled at the data layer.

## Implementation Tasks

- [x] `backend/app/api/memory.py`
- [x] `backend/app/retrieval/memory_match.py` — keyword matching against `communication_memory`
- [x] Hook into 006's approve path to write the memory row (small addition to `backend/app/api/review.py` — coordinate with whoever owns 006 to avoid a merge fight on that file)
- [x] `backend/tests/test_memory.py`
- [x] Update this file's checkboxes as you go, then open a PR into `master`
