# Implements specs/005-media-query-draft/spec.md — branch feature/005-media-query-draft.
import json

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.models import Draft, Query, QueryChannel, QueryStatus
from app.db.session import get_db
from app.retrieval.draft_builder import build_draft
from app.retrieval.service import answer_query

router = APIRouter(prefix="/api/media", tags=["media"])

CONFIRMATION = "Your query is with our communications team. A media officer will respond directly."


class MediaQueryRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    submitter_name: str = Field(min_length=1, max_length=200)
    submitter_org: str = Field(min_length=1, max_length=200)
    submitter_email: str = Field(min_length=1, max_length=320)


class MediaQueryResponse(BaseModel):
    """Deliberately carries no answer, draft text or citations — the media path
    never responds to the submitter, it only confirms receipt (specs/005)."""

    query_id: str
    status: QueryStatus
    message: str = CONFIRMATION


# POST /api/media/query — see spec. Must never return a direct answer, only a submission
# confirmation; the generated draft always goes to the Review Console.
@router.post("/query", response_model=MediaQueryResponse, status_code=status.HTTP_201_CREATED)
def submit_media_query(payload: MediaQueryRequest, db: Session = Depends(get_db)) -> MediaQueryResponse:
    # Retrieval still runs — the reviewer needs the grounded material — but
    # `above_threshold` never decides the response, only the draft's tone.
    result = answer_query(db, payload.text)

    query = Query(
        channel=QueryChannel.media,
        text=payload.text,
        confidence_score=result["confidence_score"],
        status=QueryStatus.escalated,
    )
    db.add(query)
    db.flush()

    draft_payload = build_draft(payload.text, result)
    # `queries` has no submitter columns (specs/001 owns the schema and the
    # media enquirer is not a `users` row), so the contact details travel with
    # the draft the reviewer replies from.
    draft_payload["submitter"] = {
        "name": payload.submitter_name,
        "org": payload.submitter_org,
        "email": payload.submitter_email,
    }

    db.add(
        Draft(
            query_id=query.query_id,
            draft_text=json.dumps(draft_payload),
            citations=result["citations"],
        )
    )
    db.commit()

    return MediaQueryResponse(query_id=str(query.query_id), status=QueryStatus.escalated)
