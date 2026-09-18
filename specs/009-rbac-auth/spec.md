# 009 - RBAC &amp; Auth

Branch: `feature/009-rbac-auth`
Depends on: 001
Blocks: 006, 008 (both need real role checks — until this merges they use a stub header, see below)
Docs reference: [docs/03-security-governance-compliance.md](../../docs/03-security-governance-compliance.md) Section 1, [docs/01-requirements-traceability.md](../../docs/01-requirements-traceability.md) Mandatory Design Requirement 5

## Specification

This is deliberately small and should merge early — 006 and 008 both depend on it.

1. `POST /api/auth/login` — accepts `{email, password}` against the 4 seeded demo accounts (001's `seed.py`), returns a JWT carrying `{user_id, role}`.
2. A FastAPI dependency `require_role(role: str)` that decodes the JWT and raises 403 if the role doesn't match — used by every protected endpoint.
3. Until this merges, 006 and 008 may use a temporary `X-Demo-Role` header for local testing (documented in their own branches), which this task's PR removes and replaces with the real check.
4. No self-registration. Roles are fixed to the 4 seeded accounts for the hackathon ([docs/05-mvp-scope-and-roadmap.md](../../docs/05-mvp-scope-and-roadmap.md)).
5. `GET /api/auth/me` returns the caller's `{user_id, role}` from their verified token, so the frontend shell (011) can render role-appropriate navigation without storing the role client-side.

### How other tasks use it

```python
from app.core.security import require_role

@router.get("/queue", dependencies=[Depends(require_role("comms_official"))])
def queue(): ...

# or, when the handler needs the caller's identity:
def decide(user: CurrentUser = Depends(require_role("comms_official"))): ...
```

`require_role` takes one or more roles (`require_role("comms_official", "curator_admin")` for 010's audit endpoint). A missing or invalid token is a 401; a valid token with the wrong role is a 403.

## Acceptance Criteria

- [x] Logging in as each of the 4 demo accounts returns a valid JWT with the correct role.
- [x] `require_role("curator_admin")` rejects a token with role `public` or `media` with a 403, not a silent pass-through.
- [x] Role is never trusted from a client-supplied header once this merges — only from the verified JWT.

## Implementation Tasks

- [x] `backend/app/core/security.py` — JWT issuing/verification, `require_role` dependency
- [x] `backend/app/api/auth.py` — login endpoint
- [x] `backend/tests/test_auth.py`
- [x] Remove any `X-Demo-Role` stub from 006/008 as part of this PR (coordinate timing with those owners) — nothing to remove: 006 and 008 are still unstarted stubs on `master`, so they must wire `require_role` straight in
- [x] Update this file's checkboxes as you go, then open a PR into `master`
