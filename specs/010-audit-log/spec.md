# 010 - Audit Log

Branch: `feature/010-audit-log`
Depends on: 001
Blocks: none (other tasks call a shared logging function this task provides — see coordination note)
Docs reference: [docs/03-security-governance-compliance.md](../../docs/03-security-governance-compliance.md) Section 5, demo script step 6

## Specification

1. `backend/app/core/audit.py` exposes one function, `log_event(event_type, actor_id=None, query_id=None, source_id=None, payload=None, sla_status=None)`, that writes an `audit_log` row. Build this first and publish it so 004/005/006/008 can each call it from their own branch without waiting on this task's full PR.
2. `GET /api/audit` — lists audit log entries, filterable by `query_id` or date range. Only `comms_official` and `curator_admin` roles may access it.
3. Event types to cover at minimum: `query_submitted`, `retrieval_performed`, `answer_generated`, `escalated`, `draft_created`, `review_decided`, `source_ingested`, `source_retired`, `terminology_changed`.
4. Frontend: an audit log table view, filterable, showing timestamp, event type, actor, and a link to the related query/source where applicable.

## Acceptance Criteria

- [x] Running through the full demo script produces a complete, readable trail: submission, retrieval, generation, escalation, edit, approval. Verified live: `log_event()` writes real rows to the real Postgres `audit_log` table, and `GET /api/audit` returns them via the real HTTP API. Edit/approval events (specs/006, Review Console) can't be exercised yet since 006 doesn't exist — the event types and endpoint are ready for it.
- [x] `log_event` never raises an exception that breaks the calling request. Verified live: a broken session factory (simulating a dead DB connection) prints a `[audit] WARNING: ...` to stderr and returns normally, no exception propagates. Also covered by two unit tests (broken session factory, broken `commit()`).
- [x] `/api/audit` is inaccessible to `public` and `media` roles. Uses the **real** `require_role("comms_official", "curator_admin")` dependency (specs/009-rbac-auth, merged during this task's own review) rather than the originally-planned temporary header — Task 9 landed while this task was in progress, so the real thing was wired in directly instead of building and then replacing a stub. Verified live with real JWTs: 200 for curator_admin, 403 for public, 401 with no token at all.

## Implementation Tasks

- [x] `backend/app/core/audit.py` — `log_event` (build and share this early, it's a one-file dependency for everyone else)
- [x] `backend/app/api/audit.py` — the read endpoint
- [x] `backend/tests/test_audit.py`
- [x] `frontend/src/views/AuditLog.tsx`
- [x] Update this file's checkboxes as you go, then open a PR into `master`
