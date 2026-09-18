# Implements specs/008-curator-admin/spec.md — branch feature/008-curator-admin.
from fastapi import APIRouter

router = APIRouter(prefix="/api/curator", tags=["curator"])

# POST   /api/curator/sources
# GET    /api/curator/sources
# DELETE /api/curator/sources/{id}
# GET|POST /api/curator/terminology
# Restricted to the curator_admin role (specs/009-rbac-auth).
