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

- [ ] Approving a draft in 006 creates a `communication_memory` row automatically.
- [ ] Submitting a second, related media query surfaces the just-approved response as a suggested reuse match with a visible score (matches demo script step 4).
- [ ] `/api/memory/search` returns keyword-relevant results ranked by relevance.

## Implementation Tasks

- [ ] `backend/app/api/memory.py`
- [ ] `backend/app/retrieval/memory_match.py` — keyword matching against `communication_memory`
- [ ] Hook into 006's approve path to write the memory row (small addition to `backend/app/api/review.py` — coordinate with whoever owns 006 to avoid a merge fight on that file)
- [ ] `backend/tests/test_memory.py`
- [ ] Update this file's checkboxes as you go, then open a PR into `master`
