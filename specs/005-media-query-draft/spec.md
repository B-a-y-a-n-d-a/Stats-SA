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

## Draft shape 004 and 006 share

`app/retrieval/draft_builder.build_draft(query_text, retrieval_result)` returns the one
structure both draft-producing paths write and the Review Console reads. It is stored
JSON-encoded in `drafts.draft_text` (the enforced citations are also written to the
`drafts.citations` column):

```json
{
  "headline": "...", "body": "...", "suggested_tone": "...",
  "key_figures": [{"figure": "...", "chunk_id": "...", "source": "..."}],
  "citations": [...], "information_gap": false, "confidence_score": 0.44,
  "submitter": {"name": "...", "org": "...", "email": "..."}
}
```

`key_figures` are lifted verbatim from citation quotes that survived 003's enforcement,
never from the model's prose, so a reviewer cannot mistake an unsourced number for a
sourced one. `information_gap: true` means `body` is the explicit gap statement and
`key_figures` is empty. `submitter` is only set on the media path — `queries` has no
submitter columns and a media enquirer is not a `users` row.

## Acceptance Criteria

- [x] Every submission through this endpoint results in a `drafts` row and zero direct responses to the submitter, regardless of confidence score.
- [x] A draft for a query with insufficient source coverage explicitly states the information gap rather than a fabricated figure.
- [x] The intake form never displays an "answer" — only a submission confirmation.

## Implementation Tasks

- [x] `backend/app/api/media_query.py`
- [x] `backend/app/retrieval/draft_builder.py` — shared draft structure builder (used by both 004's low-confidence branch and this task)
- [x] `backend/tests/test_media_query.py`
- [x] `frontend/src/views/MediaIntake.tsx`
- [x] `frontend/src/api/mediaQuery.ts`
- [x] Update this file's checkboxes as you go, then open a PR into `master`
