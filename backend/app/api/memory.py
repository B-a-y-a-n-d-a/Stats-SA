# Implements specs/007-communication-memory/spec.md — branch feature/007-communication-memory.
#
# GET /api/memory/search?q= — lets a Curator-Admin or Communications Official search
# communication_memory directly by keyword (specs/007 spec.md item 4). Restricted to
# comms_official and curator_admin via the real require_role dependency (specs/009,
# merged), the same two-role pattern app/api/audit.py already uses.
#
# Ranking uses the single shared scoring implementation in app.retrieval.memory_match
# (also used by GET /api/review/queue's reuse_match, app/api/review.py) so there is
# exactly one keyword-matching algorithm in the codebase.
from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.models import CommunicationMemory
from app.db.session import get_db
from app.retrieval import memory_match

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("/search")
def search_memory(
    q: str | None = QueryParam(default=None),
    db: Session = Depends(get_db),
    _user=Depends(require_role("comms_official", "curator_admin")),
):
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required.")

    memories = db.query(CommunicationMemory).all()
    results = memory_match.search(q, memories)
    return [memory_match.serialize_match(memory, score) for memory, score in results]
