# Implements specs/005-media-query-draft/spec.md — branch feature/005-media-query-draft.
from fastapi import APIRouter

router = APIRouter(prefix="/api/media", tags=["media"])

# POST /api/media/query — see spec. Must never return a direct answer, only a submission
# confirmation; the generated draft always goes to the Review Console.
