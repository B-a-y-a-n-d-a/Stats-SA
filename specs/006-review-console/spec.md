# 006 - Review Console

Branch: `feature/006-review-console`
Depends on: 001, 005 (needs drafts to review), 009 (needs the `comms_official` role to gate access — can stub role-check until 009 merges)
Blocks: none
Docs reference: [docs/01-requirements-traceability.md](../../docs/01-requirements-traceability.md) Mandatory Functional Capability 3, [docs/03-security-governance-compliance.md](../../docs/03-security-governance-compliance.md) Section 4, demo script step 3

## Specification

Where every media draft and every low-confidence public draft lands before a human sees it go out.

1. `GET /api/review/queue` — lists open `drafts` (status `escalated`), each with its source query, retrieved citations, confidence score, and any communication-memory reuse match (007).
2. `POST /api/review/{draft_id}/decide` — accepts `{decision: approve|edit_approve|reject, final_text?, reason?}`. On approve/edit_approve: writes a `reviews` row, updates `queries.status`, and (for a public-channel query only) makes the approved answer retrievable by the original requester. On reject: writes a `reviews` row with a required `reason`, returns the item to the queue rather than silently dropping it ([docs/01-requirements-traceability.md](../../docs/01-requirements-traceability.md)).
3. Every decision writes an audit log entry (010).
4. Frontend: a queue list + detail view showing the draft, its sources, confidence score, and reuse suggestions, with Approve / Edit then Approve / Reject actions.

Only the `comms_official` role can call the decide endpoint — enforce server-side, not just hide the button.

## Acceptance Criteria

- [ ] A rejected draft returns to the queue with its reason visible, never silently disappears.
- [ ] An approved public-channel draft becomes visible as the answer to the original public query.
- [ ] Calling `/api/review/{draft_id}/decide` as a non-`comms_official` user returns 403.
- [ ] The console shows the exact evidence (citations, confidence) the model used, not just the draft text (matches demo script step 3).

## Implementation Tasks

- [ ] `backend/app/api/review.py`
- [ ] `backend/tests/test_review.py`
- [ ] `frontend/src/views/ReviewConsole.tsx`
- [ ] `frontend/src/api/review.ts`
- [ ] Update this file's checkboxes as you go, then open a PR into `master`
