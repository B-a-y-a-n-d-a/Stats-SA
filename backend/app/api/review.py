# Implements specs/006-review-console/spec.md — branch feature/006-review-console.
from fastapi import APIRouter

router = APIRouter(prefix="/api/review", tags=["review"])

# GET  /api/review/queue
# POST /api/review/{draft_id}/decide
# Restricted to the comms_official role (specs/009-rbac-auth) — see spec for the
# temporary demo-role header allowed until 009 merges.
