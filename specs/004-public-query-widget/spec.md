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

- [ ] Submitting "What was the latest quarterly unemployment rate?" against a seeded QLFS document returns a cited, high-confidence answer (matches demo script step 1).
- [ ] Submitting a query with no matching content returns the escalation message, not a guess.
- [ ] Every citation rendered in the widget is a clickable link to the source URL.
- [ ] The widget embeds into the static mock Stats SA page in `frontend/mock-site/`.

## Implementation Tasks

- [ ] `backend/app/api/public_query.py`
- [ ] `backend/tests/test_public_query.py`
- [ ] `frontend/src/views/PublicWidget.tsx`
- [ ] `frontend/src/api/publicQuery.ts`
- [ ] `frontend/mock-site/index.html` — static mock Stats SA header/layout embedding the widget
- [ ] Update this file's checkboxes as you go, then open a PR into `master`
