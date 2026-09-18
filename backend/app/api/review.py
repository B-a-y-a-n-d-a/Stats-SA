# Implements specs/006-review-console/spec.md — branch feature/006-review-console.
#
# GET  /api/review/queue          — every Query still needing attention (escalated or
#                                    rejected — a rejection is not a dead end, it stays
#                                    visible with its reason so someone can reconsider).
# POST /api/review/{draft_id}/decide — approve / edit_approve / reject a Draft.
#
# Both endpoints are gated by the real require_role("comms_official") dependency
# (specs/009-rbac-auth, merged) — 401 with no/invalid token, 403 for any other role.
#
# Every Draft.draft_text in the system is a JSON string in the build_draft shape
# (app/retrieval/draft_builder.py) as of this task's public_query.py fix — media
# drafts already were (specs/005), public escalations now are too — so this router
# can safely json.loads() every Draft it touches without a format check.
#
# "reuse_match" (specs/007, Communication Memory): populated by looking up the
# single best-scoring CommunicationMemory row for this query via
# app.retrieval.memory_match.find_best_match — see _serialize_queue_item below.
# Approving a draft (decision "approve"/"edit_approve") also writes a new
# CommunicationMemory row so future queries can match against it.
import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from sqlalchemy.orm import Session

from app.core.audit import log_event
from app.core.security import CurrentUser, require_role
from app.db.models import CommunicationMemory, Draft, Query, QueryStatus, Review, ReviewDecision
from app.db.session import get_db
from app.retrieval import memory_match

router = APIRouter(prefix="/api/review", tags=["review"])


class DecideRequest(BaseModel):
    decision: ReviewDecision
    final_text: str | None = None
    reason: str | None = None


def _serialize_review(review: Review) -> dict:
    return {
        "decision": review.decision.value,
        "reason": review.reason,
        "reviewer_id": str(review.reviewer_id),
        "decided_at": review.decided_at.isoformat(),
    }


def _serialize_queue_item(query: Query, draft: Draft, db: Session) -> dict:
    history = sorted(draft.reviews, key=lambda r: r.decided_at)
    memories = db.query(CommunicationMemory).all()
    best_match = memory_match.find_best_match(query.text, memories)
    reuse_match = memory_match.serialize_match(*best_match) if best_match else None
    return {
        "query_id": str(query.query_id),
        "draft_id": str(draft.draft_id),
        "channel": query.channel.value,
        "query_text": query.text,
        "status": query.status.value,
        "confidence_score": query.confidence_score,
        "submitted_at": query.submitted_at.isoformat(),
        "draft": json.loads(draft.draft_text),
        "reuse_match": reuse_match,
        "review_history": [_serialize_review(r) for r in history],
    }


@router.get("/queue")
def get_review_queue(
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_role("comms_official")),
):
    queries = (
        db.query(Query)
        .filter(Query.status.in_([QueryStatus.escalated, QueryStatus.rejected]))
        .order_by(Query.submitted_at.desc())
        .all()
    )

    items = []
    for query in queries:
        # Exactly one Draft per escalated query in practice (see spec) — guard
        # against a query with none rather than 500ing the whole queue over it.
        draft = query.drafts[0] if query.drafts else None
        if draft is None:
            continue
        items.append(_serialize_queue_item(query, draft, db))
    return items


@router.post("/{draft_id}/decide")
def decide_review(
    draft_id: str,
    payload: DecideRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("comms_official")),
):
    try:
        draft_uuid = uuid.UUID(draft_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Draft not found.")

    draft = db.get(Draft, draft_uuid)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")

    query = db.get(Query, draft.query_id)

    if payload.decision == ReviewDecision.reject:
        if not payload.reason or not payload.reason.strip():
            raise HTTPException(status_code=400, detail="A reason is required to reject a draft.")
        final_text = payload.final_text
    else:
        # approve: final_text optional, falls back to the draft's own body.
        # edit_approve: final_text is effectively required in practice, but a
        # reviewer may "edit_approve" with no actual change — fall back the same
        # way rather than error.
        draft_payload = json.loads(draft.draft_text)
        final_text = payload.final_text or draft_payload.get("body")

    reviewer_id = uuid.UUID(user.user_id)
    decided_at = datetime.utcnow()

    review = Review(
        draft_id=draft.draft_id,
        reviewer_id=reviewer_id,
        decision=payload.decision,
        final_text=final_text,
        reason=payload.reason,
        decided_at=decided_at,
    )
    db.add(review)

    query.status = QueryStatus.rejected if payload.decision == ReviewDecision.reject else QueryStatus.approved

    if payload.decision != ReviewDecision.reject:
        # specs/007 (Communication Memory): every approved response becomes a
        # searchable precedent for the next similar question.
        db.add(
            CommunicationMemory(
                query_text=query.text,
                final_answer=final_text,
                citations=draft.citations,
                approved_by=reviewer_id,
                approved_at=decided_at,
            )
        )

    db.commit()

    log_event(
        "review_decided",
        actor_id=reviewer_id,
        query_id=query.query_id,
        payload={"decision": payload.decision.value, "draft_id": str(draft.draft_id)},
    )

    return {
        "review_id": str(review.review_id),
        "decision": payload.decision.value,
        "query_status": query.status.value,
    }
