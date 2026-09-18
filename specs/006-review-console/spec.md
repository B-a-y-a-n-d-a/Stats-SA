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

- [x] A rejected draft returns to the queue with its reason visible, never silently disappears. Verified live in a real browser: rejecting a media draft with a reason keeps it in the queue, flips its badge to "Previously rejected", and shows the reason + reviewer + timestamp under Review History — decision buttons remain available for a second look.
- [x] An approved public-channel draft becomes visible as the answer to the original public query. Verified live end-to-end: approved (with an edited final_text) a low-confidence public escalation, confirmed it dropped out of the queue, then confirmed `GET /api/public/query/{query_id}` returned the real edited answer with its real citations.
- [x] Calling `/api/review/{draft_id}/decide` as a non-`comms_official` user returns 403 (verified with real JWTs, both live and in tests); no token returns 401.
- [x] The console shows the exact evidence the model used, not just the draft text. Verified live in a real browser: headline, body, confidence score, suggested tone, and every citation as a clickable link, plus key figures and (for media) submitter details, all rendered in the expanded detail view.

**Resolved a long-standing coordination note:** `public_query.py`'s low-confidence escalation branch never used the shared `draft_builder.build_draft` structure that `media_query.py` (specs/005) already used — every Draft it wrote was a plain string, not the JSON shape this task needs to render. Fixed first, so every Draft in the system is now uniformly structured JSON. A real bug surfaced from this during live testing (see below).

**Real bug found and fixed during live browser testing (test-data artifact, not a code defect, but worth recording):** an old plain-string Draft row, written by a stale server process left running from earlier testing in this session, caused `GET /api/review/queue` to 500 on `json.loads()`. Confirms the fix above matters in practice — any pre-existing plain-string draft in a real deployment would do the same. Not something to defensively code around for this MVP (there's no rolling-migration story here), but worth knowing if `/api/review/queue` ever 500s: check for a non-JSON `draft_text` row.

**Not tested here:** the real Anthropic LLM call (no API key in this build environment, consistent with every other task touching `answer_query`) — the live checks above faked only that one piece, with everything else (Postgres, retrieval, RBAC, audit log) real.

## Implementation Tasks

- [x] `backend/app/api/review.py`
- [x] `backend/tests/test_review.py`
- [x] `frontend/src/views/ReviewConsole.tsx`
- [x] `frontend/src/api/review.ts`
- [x] Update this file's checkboxes as you go, then open a PR into `master`
