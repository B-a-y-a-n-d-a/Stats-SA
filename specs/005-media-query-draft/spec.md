# 005 - Media Query Intake &amp; Draft Generation

Branch: `feature/005-media-query-draft`
Depends on: 001, 003
Blocks: 006 (review console reads the drafts this task creates)
Docs reference: [docs/01-requirements-traceability.md](../../docs/01-requirements-traceability.md) Mandatory Functional Capability 2, demo script step 2

## Specification

The media path never auto-answers — this is the one rule that cannot be relaxed for demo convenience.

1. `POST /api/media/query` accepts `{text, submitter_name, submitter_org, submitter_email}`, tags the query `channel=media`.
2. Always calls the retrieval service (003) but ignores `above_threshold` for the response decision — a media query always produces a draft, never a direct answer.
3. Builds a structured draft: `{headline, key_figures, citations, suggested_tone}` (per [docs/05-mvp-scope-and-roadmap.md](../../docs/05-mvp-scope-and-roadmap.md)). If retrieval confidence is very low, the draft explicitly states the information gap instead of inventing content ([docs/01-requirements-traceability.md](../../docs/01-requirements-traceability.md) Mandatory Functional Capability 2).
4. Writes a `drafts` row linked to the `queries` row, status `escalated`. Never sends anything back to the submitter directly.
5. Frontend: a simple media-intake form (query + submitter details) that shows a "your query is with our communications team" confirmation, nothing else.

Coordinate with 004: both public low-confidence queries and media queries land in the same `drafts` table and the same Review Console (006) — don't build two separate draft/review systems.

## Acceptance Criteria

- [ ] Every submission through this endpoint results in a `drafts` row and zero direct responses to the submitter, regardless of confidence score.
- [ ] A draft for a query with insufficient source coverage explicitly states the information gap rather than a fabricated figure.
- [ ] The intake form never displays an "answer" — only a submission confirmation.

## Implementation Tasks

- [ ] `backend/app/api/media_query.py`
- [ ] `backend/app/retrieval/draft_builder.py` — shared draft structure builder (used by both 004's low-confidence branch and this task)
- [ ] `backend/tests/test_media_query.py`
- [ ] `frontend/src/views/MediaIntake.tsx`
- [ ] `frontend/src/api/mediaQuery.ts`
- [ ] Update this file's checkboxes as you go, then open a PR into `master`
