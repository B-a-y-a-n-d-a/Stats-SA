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

## Acceptance Criteria

- [ ] Logging in as each of the 4 demo accounts returns a valid JWT with the correct role.
- [ ] `require_role("curator_admin")` rejects a token with role `public` or `media` with a 403, not a silent pass-through.
- [ ] Role is never trusted from a client-supplied header once this merges — only from the verified JWT.

## Implementation Tasks

- [ ] `backend/app/core/security.py` — JWT issuing/verification, `require_role` dependency
- [ ] `backend/app/api/auth.py` — login endpoint
- [ ] `backend/tests/test_auth.py`
- [ ] Remove any `X-Demo-Role` stub from 006/008 as part of this PR (coordinate timing with those owners)
- [ ] Update this file's checkboxes as you go, then open a PR into `master`
