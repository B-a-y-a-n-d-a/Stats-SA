"""Tests for GET /api/review/queue, POST /api/review/{draft_id}/decide (specs/006-
review-console/spec.md), and the GET /api/public/query/{query_id} status-check
endpoint specs/006 adds to app/api/public_query.py.

Runs FastAPI's TestClient against the real app (app.main.app), with get_db
overridden to an in-memory SQLite engine (StaticPool, check_same_thread=False —
the same pattern tests/test_public_query.py, tests/test_media_query.py and
tests/test_audit.py already use successfully). Only the tables this suite touches
(queries, drafts, reviews, audit_log) are created via
Base.metadata.create_all(..., tables=[...]) — like test_audit.py, this never
creates `users`, since every FK to it (Query.submitted_by, Review.reviewer_id,
AuditLog.actor_id) is either nullable or, for Review.reviewer_id, just a plain
NOT NULL column value (a real uuid from a real JWT) with nothing here relying on
the DB enforcing the FK target itself — SQLite does not enforce FKs unless
PRAGMA foreign_keys=ON is set, which nothing here does.

Auth uses real JWTs via app.core.security.create_access_token, same as
tests/test_audit.py. log_event() (app/core/audit.py) opens its own short-lived
session via its module-level SessionLocal rather than accepting one from the
caller, so — again matching test_audit.py — an autouse fixture patches
`app.core.audit.SessionLocal` to this file's TestingSessionLocal for the
duration of each test, so decide's audit write lands in the same in-memory DB
this suite can inspect.

An autouse fixture re-applies this file's get_db override immediately before
each test and clears its tables. That override and the other test modules'
overrides all mutate the same shared `app.dependency_overrides` dict —
whichever module pytest imports/runs last would otherwise "win" for the whole
session regardless of file order, so this fixture saves and restores only the
one key it touches rather than ever calling app.dependency_overrides.clear()
(that exact blanket-clear bug already hit two other PRs in this project).
"""
import json
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db.models import AuditLog, Draft, Query, QueryChannel, QueryStatus, Review, ReviewDecision
from app.db.session import Base, get_db
from app.main import app

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # keeps the single in-memory DB alive across connections/sessions
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base.metadata.create_all(
    bind=engine,
    tables=[Query.__table__, Draft.__table__, Review.__table__, AuditLog.__table__],
)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _review_test_db():
    # Save/restore only this fixture's own key — never a blanket
    # app.dependency_overrides.clear() (see module docstring).
    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = _override_get_db
    db = TestingSessionLocal()
    try:
        db.query(Review).delete()
        db.query(Draft).delete()
        db.query(Query).delete()
        db.query(AuditLog).delete()
        db.commit()
    finally:
        db.close()
    # log_event() opens app.core.audit.SessionLocal itself — point it at this
    # suite's in-memory engine for the duration of the test.
    with patch("app.core.audit.SessionLocal", TestingSessionLocal):
        yield
    if previous_override is not None:
        app.dependency_overrides[get_db] = previous_override
    else:
        app.dependency_overrides.pop(get_db, None)


client = TestClient(app)


def _auth_header(role: str, user_id: str | None = None) -> dict:
    token = create_access_token(user_id=user_id or str(uuid.uuid4()), role=role)
    return {"Authorization": f"Bearer {token}"}


def _draft_payload(**overrides) -> dict:
    payload = {
        "headline": "What was the Q2 2026 unemployment rate?",
        "body": "The official unemployment rate was 32.9% in Q2 2026.",
        "key_figures": [{"figure": "32.9% in Q2 2026", "chunk_id": str(uuid.uuid4()), "source": "QLFS Q2 2026"}],
        "citations": [
            {
                "chunk_id": str(uuid.uuid4()),
                "source_id": str(uuid.uuid4()),
                "title": "Quarterly Labour Force Survey Q2 2026",
                "url": "https://www.statssa.gov.za/publications/P0211/P02112ndQuarter2026.pdf",
                "quote": "The official unemployment rate was 32,9% in the second quarter of 2026.",
            }
        ],
        "suggested_tone": "factual and neutral, cite the source for every figure",
        "information_gap": False,
        "confidence_score": 0.42,
    }
    payload.update(overrides)
    return payload


def _seed_query_with_draft(
    *,
    channel: QueryChannel = QueryChannel.public,
    status: QueryStatus = QueryStatus.escalated,
    confidence: float = 0.42,
    query_text: str = "What was the Q2 2026 unemployment rate?",
    draft_overrides: dict | None = None,
) -> tuple[uuid.UUID, uuid.UUID]:
    """Inserts a Query + Draft row directly (bypassing the submission endpoints,
    which have their own test suites) and returns (query_id, draft_id)."""
    payload = _draft_payload(**(draft_overrides or {}))
    db = TestingSessionLocal()
    try:
        query = Query(channel=channel, text=query_text, status=status, confidence_score=confidence)
        db.add(query)
        db.flush()
        draft = Draft(query_id=query.query_id, draft_text=json.dumps(payload), citations=payload["citations"])
        db.add(draft)
        db.commit()
        return query.query_id, draft.draft_id
    finally:
        db.close()


COMMS_OFFICIAL_ID = str(uuid.uuid4())
COMMS_OFFICIAL = _auth_header("comms_official", COMMS_OFFICIAL_ID)
CURATOR_ADMIN = _auth_header("curator_admin")
PUBLIC = _auth_header("public")
MEDIA = _auth_header("media")


# --- GET /api/review/queue — access control -----------------------------------------


def test_get_queue_without_token_returns_401():
    response = client.get("/api/review/queue")
    assert response.status_code == 401


def test_get_queue_with_public_role_returns_403():
    response = client.get("/api/review/queue", headers=PUBLIC)
    assert response.status_code == 403


# --- (a) queue lists an escalated query with its parsed draft + empty history -------


def test_queue_lists_escalated_query_with_parsed_draft_and_empty_history():
    query_id, draft_id = _seed_query_with_draft(channel=QueryChannel.media, status=QueryStatus.escalated)

    response = client.get("/api/review/queue", headers=COMMS_OFFICIAL)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    item = body[0]
    assert item["query_id"] == str(query_id)
    assert item["draft_id"] == str(draft_id)
    assert item["channel"] == "media"
    assert item["status"] == "escalated"
    assert item["confidence_score"] == 0.42
    assert item["reuse_match"] is None
    assert item["review_history"] == []
    assert item["draft"]["headline"] == "What was the Q2 2026 unemployment rate?"
    assert item["draft"]["body"] == "The official unemployment rate was 32.9% in Q2 2026."
    assert item["draft"]["information_gap"] is False
    assert set(item.keys()) == {
        "query_id",
        "draft_id",
        "channel",
        "query_text",
        "status",
        "confidence_score",
        "submitted_at",
        "draft",
        "reuse_match",
        "review_history",
    }


def test_queue_parses_media_draft_including_submitter_key():
    _seed_query_with_draft(
        channel=QueryChannel.media,
        draft_overrides={"submitter": {"name": "Thandi Nkosi", "org": "Daily Maverick", "email": "t@example.com"}},
    )

    body = client.get("/api/review/queue", headers=COMMS_OFFICIAL).json()

    assert body[0]["draft"]["submitter"]["org"] == "Daily Maverick"


# --- (b) queue excludes an approved query --------------------------------------------


def test_queue_excludes_approved_query():
    _seed_query_with_draft(status=QueryStatus.approved)

    body = client.get("/api/review/queue", headers=COMMS_OFFICIAL).json()

    assert body == []


# --- (c) queue still includes a rejected query, with the rejection in history -------


def test_queue_includes_rejected_query_with_history():
    query_id, draft_id = _seed_query_with_draft(status=QueryStatus.rejected)
    db = TestingSessionLocal()
    try:
        db.add(
            Review(
                draft_id=draft_id,
                reviewer_id=uuid.UUID(COMMS_OFFICIAL_ID),
                decision=ReviewDecision.reject,
                reason="Figure is stale, needs the newer release.",
            )
        )
        db.commit()
    finally:
        db.close()

    body = client.get("/api/review/queue", headers=COMMS_OFFICIAL).json()

    assert len(body) == 1
    item = body[0]
    assert item["status"] == "rejected"
    assert len(item["review_history"]) == 1
    entry = item["review_history"][0]
    assert entry["decision"] == "reject"
    assert entry["reason"] == "Figure is stale, needs the newer release."
    assert entry["reviewer_id"] == COMMS_OFFICIAL_ID


# --- (d) approve --------------------------------------------------------------------


def test_approve_sets_query_approved_and_creates_review_with_reviewer_id():
    query_id, draft_id = _seed_query_with_draft()

    response = client.post(f"/api/review/{draft_id}/decide", json={"decision": "approve"}, headers=COMMS_OFFICIAL)

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "approve"
    assert body["query_status"] == "approved"
    uuid.UUID(body["review_id"])  # a real uuid string

    db = TestingSessionLocal()
    try:
        query = db.get(Query, query_id)
        assert query.status == QueryStatus.approved
        review = db.get(Review, uuid.UUID(body["review_id"]))
        assert review is not None
        assert review.draft_id == draft_id
        assert str(review.reviewer_id) == COMMS_OFFICIAL_ID
        assert review.decision == ReviewDecision.approve
        # final_text omitted -> falls back to the draft's own body.
        assert review.final_text == "The official unemployment rate was 32.9% in Q2 2026."
    finally:
        db.close()

    # log_event("review_decided", ...) fired.
    db = TestingSessionLocal()
    try:
        logs = db.query(AuditLog).filter(AuditLog.event_type == "review_decided").all()
        assert len(logs) == 1
        assert logs[0].query_id == query_id
        assert str(logs[0].actor_id) == COMMS_OFFICIAL_ID
        assert logs[0].payload["decision"] == "approve"
    finally:
        db.close()


# --- (e) edit_approve stores the provided final_text ---------------------------------


def test_edit_approve_stores_provided_final_text():
    query_id, draft_id = _seed_query_with_draft()

    response = client.post(
        f"/api/review/{draft_id}/decide",
        json={"decision": "edit_approve", "final_text": "The official rate was 32.9%, per QLFS Q2 2026."},
        headers=COMMS_OFFICIAL,
    )

    assert response.status_code == 200
    assert response.json()["query_status"] == "approved"

    db = TestingSessionLocal()
    try:
        review = db.query(Review).filter(Review.draft_id == draft_id).one()
        assert review.decision == ReviewDecision.edit_approve
        assert review.final_text == "The official rate was 32.9%, per QLFS Q2 2026."
    finally:
        db.close()


def test_edit_approve_without_final_text_falls_back_to_draft_body():
    _, draft_id = _seed_query_with_draft()

    response = client.post(f"/api/review/{draft_id}/decide", json={"decision": "edit_approve"}, headers=COMMS_OFFICIAL)

    assert response.status_code == 200
    db = TestingSessionLocal()
    try:
        review = db.query(Review).filter(Review.draft_id == draft_id).one()
        assert review.final_text == "The official unemployment rate was 32.9% in Q2 2026."
    finally:
        db.close()


# --- (f) reject without a reason returns 400 ------------------------------------------


@pytest.mark.parametrize("body", [{"decision": "reject"}, {"decision": "reject", "reason": ""}, {"decision": "reject", "reason": "   "}])
def test_reject_without_reason_returns_400(body):
    _, draft_id = _seed_query_with_draft()

    response = client.post(f"/api/review/{draft_id}/decide", json=body, headers=COMMS_OFFICIAL)

    assert response.status_code == 400


# --- (g) reject with a reason succeeds; item stays in the queue as "rejected" --------


def test_reject_with_reason_succeeds_and_stays_in_queue():
    query_id, draft_id = _seed_query_with_draft()

    response = client.post(
        f"/api/review/{draft_id}/decide",
        json={"decision": "reject", "reason": "Needs a more recent source."},
        headers=COMMS_OFFICIAL,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "reject"
    assert body["query_status"] == "rejected"

    queue = client.get("/api/review/queue", headers=COMMS_OFFICIAL).json()
    assert len(queue) == 1
    item = queue[0]
    assert item["query_id"] == str(query_id)
    assert item["status"] == "rejected"
    assert item["review_history"][0]["reason"] == "Needs a more recent source."


# --- (h)/(i) decide — access control --------------------------------------------------


def test_decide_as_non_comms_official_returns_403():
    _, draft_id = _seed_query_with_draft()

    response = client.post(f"/api/review/{draft_id}/decide", json={"decision": "approve"}, headers=MEDIA)

    assert response.status_code == 403


def test_decide_with_no_token_returns_401():
    _, draft_id = _seed_query_with_draft()

    response = client.post(f"/api/review/{draft_id}/decide", json={"decision": "approve"})

    assert response.status_code == 401


def test_decide_with_curator_admin_role_returns_403():
    _, draft_id = _seed_query_with_draft()

    response = client.post(f"/api/review/{draft_id}/decide", json={"decision": "approve"}, headers=CURATOR_ADMIN)

    assert response.status_code == 403


def test_decide_unknown_draft_id_returns_404():
    response = client.post(
        f"/api/review/{uuid.uuid4()}/decide", json={"decision": "approve"}, headers=COMMS_OFFICIAL
    )

    assert response.status_code == 404


# --- (j) GET /api/public/query/{query_id} ---------------------------------------------


@pytest.mark.parametrize("status", [QueryStatus.escalated, QueryStatus.rejected])
def test_public_status_check_returns_escalation_message_while_pending(status):
    query_id, _ = _seed_query_with_draft(status=status)

    response = client.get(f"/api/public/query/{query_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "escalated"
    from app.api.public_query import ESCALATION_MESSAGE

    assert body["message"] == ESCALATION_MESSAGE


def test_public_status_check_returns_real_answer_after_approval():
    query_id, draft_id = _seed_query_with_draft(
        query_text="What was the Q2 2026 unemployment rate?", confidence=0.42
    )

    decide_response = client.post(
        f"/api/review/{draft_id}/decide",
        json={"decision": "edit_approve", "final_text": "It was 32.9% in Q2 2026, per Stats SA's QLFS release."},
        headers=COMMS_OFFICIAL,
    )
    assert decide_response.status_code == 200

    response = client.get(f"/api/public/query/{query_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answered"
    assert body["answer"] == "It was 32.9% in Q2 2026, per Stats SA's QLFS release."
    assert body["confidence_score"] == 0.42
    assert len(body["citations"]) == 1
    assert body["citations"][0]["url"].startswith("https://")


def test_public_status_check_answered_query_returns_404():
    db = TestingSessionLocal()
    try:
        query = Query(
            channel=QueryChannel.public,
            text="Already answered directly",
            status=QueryStatus.answered,
            confidence_score=0.9,
        )
        db.add(query)
        db.commit()
        query_id = query.query_id
    finally:
        db.close()

    response = client.get(f"/api/public/query/{query_id}")

    assert response.status_code == 404


def test_public_status_check_unknown_query_id_returns_404():
    response = client.get(f"/api/public/query/{uuid.uuid4()}")
    assert response.status_code == 404
