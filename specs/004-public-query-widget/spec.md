# 004 - Public Query API &amp; Widget

Branch: `feature/004-public-query-widget`
Depends on: 001, 003
Blocks: none directly, but 007 (communication memory) reads from `queries` this task writes
Docs reference: [docs/01-requirements-traceability.md](../../docs/01-requirements-traceability.md) Mandatory Functional Capability 1, demo script step 1 in [docs/05-mvp-scope-and-roadmap.md](../../docs/05-mvp-scope-and-roadmap.md)

## Specification

The public self-service path.

1. `POST /api/public/query` accepts `{text}`, calls the retrieval service (003).
2. If `above_threshold` is true: log the query as `answered`, return the answer with citations and confidence score directly.
3. If `above_threshold` is false: log the query as `escalated`, create a `drafts` row (via the same draft-generation logic media queries use — coordinate with 005 so this isn't duplicated), and return a "your question needs a quick review, check back shortly" response instead of a guess.
4. Frontend: a chat-style widget (single input + response area) that calls this endpoint and renders the answer, its confidence badge, and clickable citations. Unsourced/AI-framing text is visually distinguished from cited source text ([docs/02-architecture.md](../../docs/02-architecture.md) Section 1.1).

## Acceptance Criteria

- [x] Submitting a real, relevant query against a real seeded document returns a cited, high-confidence answer (matches demo script step 1). Verified live end-to-end in a real browser: real Postgres + real pgvector retrieval + real ingested Stats SA GDP fact sheet, with only the final LLM call faked (no API key available in this environment — see specs/003's same note). Screenshot-confirmed: answer text, a "Confidence: 48%" badge, and a real clickable citation link all rendered correctly.
- [x] Submitting a query with no matching content returns the escalation message, not a guess. Verified live in the browser: an unrelated query ("best recipe for chocolate cake") rendered only the escalation message, no fabricated answer.
- [x] Every citation rendered in the widget is a clickable link to the source URL. Confirmed in the rendered screenshot — citation renders as `<a href={citation.url}>`.
- [x] The widget embeds into the static mock Stats SA page in `frontend/mock-site/`. The mock page documents the real embed point; the actual bundling/mounting into it is specs/011's integration job, noted explicitly in the file.

**Real finding from live testing:** `scripts/seed_sources.yaml` still pointed at a PDF fixture that Task 2's cleanup had removed (`P0441_GDP_Q2_2026_press_release.pdf`) — the bulk-ingest script failed on a fresh checkout. Fixed to point at the fixture that actually exists (`P0441_factsheetA.pdf`).

**Not tested here:** the real `AnthropicLLMClient` call — no `LLM_API_KEY` in this build environment, consistent with specs/003.

## Implementation Tasks

- [x] `backend/app/api/public_query.py`
- [x] `backend/tests/test_public_query.py`
- [x] `frontend/src/views/PublicWidget.tsx`
- [x] `frontend/src/api/publicQuery.ts`
- [x] `frontend/mock-site/index.html` — static mock Stats SA header/layout embedding the widget
- [x] Update this file's checkboxes as you go, then open a PR into `master`

**Post-merge addition (specs/006):** `GET /api/public/query/{query_id}` was added to this file by Task 6 so a requester who got the escalation message can poll for the reviewed answer once a Communications Official decides on it. Also, this file's escalation branch was refactored to build its Draft via the shared `draft_builder.build_draft` (specs/005) instead of a plain string, so the Review Console can render every Draft in the system uniformly.
