# Implements specs/010-audit-log/spec.md — branch feature/010-audit-log.
from fastapi import APIRouter

router = APIRouter(prefix="/api/audit", tags=["audit"])

# GET /api/audit — restricted to comms_official and curator_admin roles.
