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

- [ ] Uploading a new PDF and triggering ingestion makes it queryable within the demo (matches demo script step 5 — "ask a question only that document can answer").
- [ ] Re-uploading the same source creates a new version rather than overwriting.
- [ ] Calling any `/api/curator/*` endpoint as a non-`curator_admin` user returns 403.
- [ ] The terminology UI clearly labels entries as "not yet dual-approved" per the MVP scope note above.

## Implementation Tasks

- [ ] `backend/app/api/curator.py`
- [ ] `backend/tests/test_curator.py`
- [ ] `frontend/src/views/CuratorAdmin.tsx`
- [ ] `frontend/src/api/curator.ts`
- [ ] Update this file's checkboxes as you go, then open a PR into `master`
