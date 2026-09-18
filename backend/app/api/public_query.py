# Implements specs/004-public-query-widget/spec.md — branch feature/004-public-query-widget.
from fastapi import APIRouter

router = APIRouter(prefix="/api/public", tags=["public"])

# POST /api/public/query — see spec for request/response shape and behavior.
