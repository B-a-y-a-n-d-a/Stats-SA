"""Tests for app.retrieval.memory_match, the specs/007 additions to
POST /api/review/{draft_id}/decide and GET /api/review/queue's reuse_match
(app/api/review.py), and GET /api/memory/search (app/api/memory.py) —
specs/007-communication-memory/spec.md.

Runs FastAPI's TestClient against the real app (app.main.app), with get_db
overridden to an in-memory SQLite engine (StaticPool, check_same_thread=False —
the same pattern tests/test_review.py and tests/test_audit.py already use
successfully). Only the tables this suite touches (queries, drafts, reviews,
communication_memory, audit_log) are created via Base.metadata.create_all(...,
tables=[...]) — `users` is never created, since every FK to it here (Review.
reviewer_id, CommunicationMemory.approved_by) is just a plain NOT NULL column
value (a real uuid from a real JWT) with nothing here relying on the DB
enforcing the FK target itself — SQLite does not enforce FKs unless PRAGMA
foreign_keys=ON is set, which nothing here does.

Auth uses real JWTs via app.core.security.create_access_token, same as
tests/test_review.py. log_event() (app/core/audit.py) opens its own short-lived
session via its module-level SessionLocal rather than accepting one from the
caller, so — again matching test_review.py — an autouse fixture patches
`app.core.audit.SessionLocal` to this file's TestingSessionLocal for the
duration of each test.

An autouse fixture re-applies this file's get_db override immediately before
each test and clears its tables. That override and the other test modules'
overrides all mutate the same shared `app.dependency_overrides` dict —
whichever module pytest imports/runs last would otherwise "win" for the whole
session regardless of file order, so this fixture saves and restores only the
one key it touches rather than ever calling app.dependency_overrides.clear()
(that exact blanket-clear bug already hit two other PRs in this project this
session — do not reintroduce it).
"""
import json
import uuid
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db.models import AuditLog, CommunicationMemory, Draft, Query, QueryChannel, QueryStatus, Review
from app.db.session import Base, get_db
from app.main import app
from app.retrieval import memory_match

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # keeps the single in-memory DB alive across connections/sessions
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base.metadata.create_all(
    bind=engine,
    tables=[Query.__table__, Draft.__table__, Review.__table__, CommunicationMemory.__table__, AuditLog.__table__],
)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _memory_test_db():
    # Save/restore only this fixture's own key — never a blanket
    # app.dependency_overrides.clear() (see module docstring).
    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = _override_get_db
    db = TestingSessionLocal()
    try:
        db.query(Review).delete()
        db.query(Draft).delete()
        db.query(Query).delete()
        db.query(CommunicationMemory).delete()
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


# --- (a) memory_match — pure unit tests, no HTTP -------------------------------------


def _memory(query_text: str) -> SimpleNamespace:
    # A plain object with just the attribute memory_match.find_best_match/search
    # actually read (query_text) — proves the module needs nothing DB-specific.
    return SimpleNamespace(query_text=query_text)


def test_find_best_match_scores_exact_keyword_match_high():
    candidate = _memory("What was the Q2 2026 unemployment rate?")

    result = memory_match.find_best_match("What was the Q2 2026 unemployment rate?", [candidate])

    assert result is not None
    matched, score = result
    assert matched is candidate
    assert score == pytest.approx(1.0)


def test_find_best_match_returns_none_for_unrelated_query():
    candidate = _memory("What was the Q2 2026 unemployment rate?")

    result = memory_match.find_best_match("Population growth in Limpopo province last census", [candidate])

    assert result is None


def test_find_best_match_returns_none_for_empty_candidate_list():
    assert memory_match.find_best_match("What was the Q2 2026 unemployment rate?", []) is None


def test_find_best_match_ranks_multiple_candidates_best_first():
    weak = _memory("What is the population of South Africa?")
    strong = _memory("What was the Q2 2026 unemployment rate?")

    result = memory_match.find_best_match("What was the unemployment rate in Q2 2026?", [weak, strong])

    assert result is not None
    matched, score = result
    assert matched is strong
    assert score > 0


def test_search_returns_all_positive_matches_sorted_descending_capped_at_top_k():
    # exact shares every one of the query's tokens (score 1.0); weaker shares
    # only some of them ("what", "was", "the", "2026") so it necessarily scores
    # lower — the score formula is deliberately asymmetric (see memory_match.py),
    # so a candidate merely being a superset of the query's tokens is not enough
    # to make it score lower than an exact match.
    exact = _memory("What was the Q2 2026 unemployment rate?")
    weaker = _memory("What was the population of South Africa in 2026?")
    unrelated = _memory("Population growth in Limpopo province last census")

    results = memory_match.search("What was the Q2 2026 unemployment rate?", [weaker, unrelated, exact], top_k=10)

    assert [c.query_text for c, _ in results] == [exact.query_text, weaker.query_text]
    assert results[0][1] > results[1][1]
    assert all(score > 0 for _, score in results)


def test_search_caps_results_at_top_k():
    candidates = [_memory("What was the Q2 2026 unemployment rate?") for _ in range(5)]

    results = memory_match.search("What was the Q2 2026 unemployment rate?", candidates, top_k=2)

    assert len(results) == 2


# --- (b) approving a draft creates a CommunicationMemory row -------------------------


def test_approve_creates_communication_memory_row_with_expected_fields():
    query_id, draft_id = _seed_query_with_draft(query_text="What was the Q2 2026 unemployment rate?")

    response = client.post(f"/api/review/{draft_id}/decide", json={"decision": "approve"}, headers=COMMS_OFFICIAL)

    assert response.status_code == 200
    db = TestingSessionLocal()
    try:
        rows = db.query(CommunicationMemory).all()
        assert len(rows) == 1
        memory = rows[0]
        assert memory.query_text == "What was the Q2 2026 unemployment rate?"
        assert memory.final_answer == "The official unemployment rate was 32.9% in Q2 2026."
        assert len(memory.citations) == 1
        assert memory.citations[0]["title"] == "Quarterly Labour Force Survey Q2 2026"
        assert str(memory.approved_by) == COMMS_OFFICIAL_ID
        assert memory.approved_at is not None
    finally:
        db.close()


def test_edit_approve_creates_communication_memory_row_with_edited_final_text():
    _, draft_id = _seed_query_with_draft()

    response = client.post(
        f"/api/review/{draft_id}/decide",
        json={"decision": "edit_approve", "final_text": "The official rate was 32.9%, per QLFS Q2 2026."},
        headers=COMMS_OFFICIAL,
    )

    assert response.status_code == 200
    db = TestingSessionLocal()
    try:
        memory = db.query(CommunicationMemory).one()
        assert memory.final_answer == "The official rate was 32.9%, per QLFS Q2 2026."
    finally:
        db.close()


# --- (c) rejecting a draft does NOT create a CommunicationMemory row -----------------


def test_reject_does_not_create_communication_memory_row():
    _, draft_id = _seed_query_with_draft()

    response = client.post(
        f"/api/review/{draft_id}/decide",
        json={"decision": "reject", "reason": "Needs a more recent source."},
        headers=COMMS_OFFICIAL,
    )

    assert response.status_code == 200
    db = TestingSessionLocal()
    try:
        assert db.query(CommunicationMemory).count() == 0
    finally:
        db.close()


# --- (d)/(e) GET /api/review/queue — reuse_match populated from prior approvals -------


def test_queue_shows_prior_approval_as_reuse_match_for_a_related_query():
    _, first_draft_id = _seed_query_with_draft(query_text="What was the Q2 2026 unemployment rate?")
    approve_response = client.post(
        f"/api/review/{first_draft_id}/decide", json={"decision": "approve"}, headers=COMMS_OFFICIAL
    )
    assert approve_response.status_code == 200
    db = TestingSessionLocal()
    try:
        memory_id = str(db.query(CommunicationMemory).one().memory_id)
    finally:
        db.close()

    related_query_id, _ = _seed_query_with_draft(
        query_text="What is the Q2 2026 unemployment rate in Gauteng?", status=QueryStatus.escalated
    )

    body = client.get("/api/review/queue", headers=COMMS_OFFICIAL).json()

    item = next(i for i in body if i["query_id"] == str(related_query_id))
    assert item["reuse_match"] is not None
    assert item["reuse_match"]["memory_id"] == memory_id
    assert item["reuse_match"]["query_text"] == "What was the Q2 2026 unemployment rate?"
    assert item["reuse_match"]["final_answer"] == "The official unemployment rate was 32.9% in Q2 2026."
    assert item["reuse_match"]["approved_by"] == COMMS_OFFICIAL_ID
    assert item["reuse_match"]["score"] > 0


def test_queue_shows_null_reuse_match_for_an_unrelated_query():
    _, first_draft_id = _seed_query_with_draft(query_text="What was the Q2 2026 unemployment rate?")
    client.post(f"/api/review/{first_draft_id}/decide", json={"decision": "approve"}, headers=COMMS_OFFICIAL)

    unrelated_query_id, _ = _seed_query_with_draft(
        query_text="Population growth in Limpopo province last census", status=QueryStatus.escalated
    )

    body = client.get("/api/review/queue", headers=COMMS_OFFICIAL).json()

    item = next(i for i in body if i["query_id"] == str(unrelated_query_id))
    assert item["reuse_match"] is None


def test_queue_shows_null_reuse_match_when_memory_repository_is_empty():
    query_id, _ = _seed_query_with_draft()

    body = client.get("/api/review/queue", headers=COMMS_OFFICIAL).json()

    assert body[0]["query_id"] == str(query_id)
    assert body[0]["reuse_match"] is None


# --- (f) GET /api/memory/search -------------------------------------------------------


def _seed_memory(
    *,
    query_text: str = "What was the Q2 2026 unemployment rate?",
    final_answer: str = "The official unemployment rate was 32.9% in Q2 2026.",
    approved_by: str | None = None,
) -> uuid.UUID:
    db = TestingSessionLocal()
    try:
        memory = CommunicationMemory(
            query_text=query_text,
            final_answer=final_answer,
            citations=[{"title": "QLFS Q2 2026", "url": "https://www.statssa.gov.za/"}],
            approved_by=uuid.UUID(approved_by or COMMS_OFFICIAL_ID),
        )
        db.add(memory)
        db.commit()
        return memory.memory_id
    finally:
        db.close()


def test_search_returns_matching_entries_ranked_by_score():
    # exact shares every one of the search query's tokens (score 1.0); weaker
    # shares only some of them, so it necessarily scores lower — see the
    # equivalent note in test_search_returns_all_positive_matches_sorted_
    # descending_capped_at_top_k for why a superset candidate is not a
    # reliable way to construct a strictly-lower score.
    exact_id = _seed_memory(query_text="What was the Q2 2026 unemployment rate?")
    weaker_id = _seed_memory(
        query_text="What was the population of South Africa in 2026?",
        final_answer="A separate answer about population, not unemployment.",
    )
    _seed_memory(
        query_text="Population growth in Limpopo province last census",
        final_answer="Agriculture employment figures.",
    )

    response = client.get(
        "/api/memory/search", params={"q": "What was the Q2 2026 unemployment rate?"}, headers=COMMS_OFFICIAL
    )

    assert response.status_code == 200
    body = response.json()
    assert [item["memory_id"] for item in body] == [str(exact_id), str(weaker_id)]
    assert body[0]["score"] > body[1]["score"]
    assert all(item["score"] > 0 for item in body)
    assert set(body[0].keys()) == {
        "memory_id",
        "query_text",
        "final_answer",
        "citations",
        "approved_by",
        "approved_at",
        "score",
    }


def test_search_missing_q_returns_400():
    response = client.get("/api/memory/search", headers=COMMS_OFFICIAL)
    assert response.status_code == 400


def test_search_empty_q_returns_400():
    response = client.get("/api/memory/search", params={"q": "   "}, headers=COMMS_OFFICIAL)
    assert response.status_code == 400


def test_search_with_no_matches_returns_empty_array():
    _seed_memory(query_text="What was the Q2 2026 unemployment rate?")

    response = client.get(
        "/api/memory/search", params={"q": "Population growth in Limpopo province last census"}, headers=COMMS_OFFICIAL
    )

    assert response.status_code == 200
    assert response.json() == []


# --- (g) GET /api/memory/search — access control --------------------------------------


def test_search_without_token_returns_401():
    response = client.get("/api/memory/search", params={"q": "unemployment"})
    assert response.status_code == 401


def test_search_with_public_role_returns_403():
    response = client.get("/api/memory/search", params={"q": "unemployment"}, headers=PUBLIC)
    assert response.status_code == 403


def test_search_with_media_role_returns_403():
    response = client.get("/api/memory/search", params={"q": "unemployment"}, headers=MEDIA)
    assert response.status_code == 403


def test_search_with_comms_official_role_returns_200():
    response = client.get("/api/memory/search", params={"q": "unemployment"}, headers=COMMS_OFFICIAL)
    assert response.status_code == 200


def test_search_with_curator_admin_role_returns_200():
    response = client.get("/api/memory/search", params={"q": "unemployment"}, headers=CURATOR_ADMIN)
    assert response.status_code == 200
