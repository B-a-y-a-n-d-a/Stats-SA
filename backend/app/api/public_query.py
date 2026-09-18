# Implements specs/004-public-query-widget/spec.md — branch feature/004-public-query-widget.
# GET /api/public/query/{query_id} added by specs/006-review-console/spec.md — lets a
# requester who got the escalation message poll for the reviewed answer.
#
# The public self-service path: calls the shared retrieval + confidence gate
# (app/retrieval/service.py, specs/003) and either returns a cited answer
# directly or escalates to the review queue via a Draft row. Never returns a
# guess — see docs/02-architecture.md Section 1.1.
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.audit import log_event
from app.db.models import Draft, Query, QueryChannel, QueryStatus, Review
from app.db.session import get_db
from app.retrieval.draft_builder import build_draft
from app.retrieval.service import answer_query

router = APIRouter(prefix="/api/public", tags=["public"])

ESCALATION_MESSAGE = "Your question needs a quick review by our team — check back shortly."


class PublicQueryRequest(BaseModel):
    text: str = Field(..., min_length=1)


@router.post("/query")
def submit_public_query(request: PublicQueryRequest, db: Session = Depends(get_db)):
    result = answer_query(db, request.text)

    query = Query(
        channel=QueryChannel.public,
        text=request.text,
        status=QueryStatus.answered if result["above_threshold"] else QueryStatus.escalated,
        confidence_score=result["confidence_score"],
    )
    db.add(query)
    db.commit()

    log_event("query_submitted", query_id=query.query_id, payload={"channel": "public"})

    if result["above_threshold"]:
        log_event("answer_generated", query_id=query.query_id)
        return {
            "status": "answered",
            "answer": result["answer_text"],
            "confidence_score": result["confidence_score"],
            "citations": result["citations"],
        }

    # specs/005 (media path) landed with a shared draft shape in draft_builder.py —
    # this now builds the same {headline, body, key_figures, citations,
    # suggested_tone, information_gap, confidence_score} JSON structure (minus the
    # media-only "submitter" key) so the Review Console (specs/006) can render every
    # Draft in the system uniformly. See app/api/media_query.py for the media
    # equivalent of this block.
    draft_payload = build_draft(request.text, result)
    draft = Draft(
        query_id=query.query_id,
        draft_text=json.dumps(draft_payload),
        citations=result["citations"],
    )
    db.add(draft)
    db.commit()

    log_event("escalated", query_id=query.query_id)

    return {
        "status": "escalated",
        "message": ESCALATION_MESSAGE,
        "query_id": str(query.query_id),
    }


# GET /api/public/query/{query_id} — specs/006. No auth, matching POST /query above:
# the requester who got the escalation message polls this to find out once a
# comms_official has decided on their draft (specs/006's decide endpoint). A
# rejected-but-still-queued query reads identically to a still-open one — the
# requester never sees internal review mechanics, only "still working on it" or
# a final answer.
@router.get("/query/{query_id}")
def get_public_query_status(query_id: str, db: Session = Depends(get_db)):
    try:
        query_uuid = uuid.UUID(query_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Query not found.")

    query = db.get(Query, query_uuid)
    if query is None:
        raise HTTPException(status_code=404, detail="Query not found.")

    if query.status in (QueryStatus.escalated, QueryStatus.rejected):
        return {"status": "escalated", "message": ESCALATION_MESSAGE}

    if query.status == QueryStatus.approved:
        draft = db.query(Draft).filter(Draft.query_id == query.query_id).first()
        review = (
            db.query(Review)
            .filter(Review.draft_id == draft.draft_id)
            .order_by(Review.decided_at.desc())
            .first()
        )
        return {
            "status": "answered",
            "answer": review.final_text,
            "confidence_score": query.confidence_score,
            "citations": draft.citations,
        }

    # status == "answered": answered directly in the original POST response, and
    # nothing about that answer is persisted anywhere else to re-serve here.
    raise HTTPException(
        status_code=404,
        detail="This query was answered directly at submission time; there is nothing further to check.",
    )
