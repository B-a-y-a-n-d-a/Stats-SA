# Implements specs/004-public-query-widget/spec.md — branch feature/004-public-query-widget.
#
# The public self-service path: calls the shared retrieval + confidence gate
# (app/retrieval/service.py, specs/003) and either returns a cited answer
# directly or escalates to the review queue via a Draft row. Never returns a
# guess — see docs/02-architecture.md Section 1.1.
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.audit import log_event
from app.db.models import Draft, Query, QueryChannel, QueryStatus
from app.db.session import get_db
from app.retrieval.service import answer_query

router = APIRouter(prefix="/api/public", tags=["public"])

ESCALATION_MESSAGE = "Your question needs a quick review by our team — check back shortly."
# Shown as the Draft's own text when the LLM gave no answer at all (empty registry
# match or the confidence gate rejected it) — reviewers still need a placeholder to
# open in the Review Console, not a blank field.
NO_ANSWER_PLACEHOLDER = "Insufficient information to answer confidently."


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

    # NOTE: this Draft-creation block duplicates what the media path (specs/005) will
    # also need for its own escalations ("via the same draft-generation logic media
    # queries use" per this spec's own text) — a shared helper (e.g. draft_builder.py)
    # is the right long-term home for it. specs/005 has not landed yet as of this
    # writing and that module is explicitly owned by that task, so this inlines the
    # minimal Draft construction here rather than introducing a shared module out of
    # turn. Refactor this into whatever helper specs/005 lands once it exists.
    draft = Draft(
        query_id=query.query_id,
        draft_text=result["answer_text"] or NO_ANSWER_PLACEHOLDER,
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
