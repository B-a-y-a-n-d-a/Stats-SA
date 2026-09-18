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

- [ ] Running through the full demo script produces a complete, readable trail: submission, retrieval, generation, escalation, edit, approval (matches demo script step 6).
- [ ] `log_event` never raises an exception that breaks the calling request (log failures are swallowed and separately alerted, not fatal to the user-facing action).
- [ ] `/api/audit` is inaccessible to `public` and `media` roles.

## Implementation Tasks

- [ ] `backend/app/core/audit.py` — `log_event` (build and share this early, it's a one-file dependency for everyone else)
- [ ] `backend/app/api/audit.py` — the read endpoint
- [ ] `backend/tests/test_audit.py`
- [ ] `frontend/src/views/AuditLog.tsx`
- [ ] Update this file's checkboxes as you go, then open a PR into `master`
