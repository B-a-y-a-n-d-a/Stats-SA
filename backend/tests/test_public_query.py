"""Tests for POST /api/public/query (specs/004-public-query-widget/spec.md).

Runs FastAPI's TestClient against the real app (app.main.app) with two things
swapped out so the suite is deterministic and needs no live LLM or embedding
model:

  * app.retrieval.service.answer_query is patched at its import site in
    app.api.public_query, with a canned high-confidence result for the
    "answered" test and a canned low-confidence (above_threshold=False)
    result for the "escalated" test.
  * the get_db dependency is overridden to hand out sessions against an
    in-memory SQLite engine instead of the real Postgres one, since a live
    Postgres is not assumed to be reachable in this environment.

That SQLite engine only ever creates the `queries` and `drafts` tables (via
Base.metadata.create_all(..., tables=[...])) — Chunk/Source, and in particular
Chunk's pgvector-specific `embedding` column, are never created or touched by
this file. That's safe here because answer_query is fully mocked, so
app/retrieval/search.py (the only thing that reads Chunk.embedding) never
runs. pgvector columns are exercised by the live-Postgres suite in
tests/test_retrieval.py instead, not here.
"""
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Draft, Query
from app.db.session import Base, get_db
from app.main import app

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # keeps the single in-memory DB alive across connections/sessions
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base.metadata.create_all(bind=engine, tables=[Query.__table__, Draft.__table__])


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db

client = TestClient(app)

HIGH_CONFIDENCE_RESULT = {
    "answer_text": "The latest quarterly unemployment rate was 32.9% (Q2 2026).",
    "citations": [
        {
            "chunk_id": str(uuid.uuid4()),
            "source_id": str(uuid.uuid4()),
            "title": "Quarterly Labour Force Survey Q2 2026",
            "url": "https://www.statssa.gov.za/publications/P0211/P02112ndQuarter2026.pdf",
            "quote": "The official unemployment rate was 32,9% in the second quarter of 2026.",
        }
    ],
    "confidence_score": 0.52,
    "above_threshold": True,
}

LOW_CONFIDENCE_RESULT = {
    "answer_text": None,
    "citations": [],
    "confidence_score": 0.12,
    "above_threshold": False,
}


@patch("app.api.public_query.answer_query")
def test_answered_response_includes_answer_confidence_and_real_citation_links(mock_answer_query):
    mock_answer_query.return_value = HIGH_CONFIDENCE_RESULT

    response = client.post(
        "/api/public/query",
        json={"text": "What was the latest quarterly unemployment rate?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answered"
    assert body["answer"] == HIGH_CONFIDENCE_RESULT["answer_text"]
    assert body["confidence_score"] == HIGH_CONFIDENCE_RESULT["confidence_score"]
    assert len(body["citations"]) == 1
    citation = body["citations"][0]
    assert citation["chunk_id"] == HIGH_CONFIDENCE_RESULT["citations"][0]["chunk_id"]
    # Contract requires every rendered citation to be a real clickable link.
    assert citation["url"] == HIGH_CONFIDENCE_RESULT["citations"][0]["url"]
    assert citation["url"].startswith("https://")


@patch("app.api.public_query.answer_query")
def test_escalated_response_has_no_fabricated_answer_and_includes_query_id(mock_answer_query):
    mock_answer_query.return_value = LOW_CONFIDENCE_RESULT

    response = client.post(
        "/api/public/query",
        json={"text": "some question with no matching registry content"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "escalated"
    assert body["message"]
    # No answer/citations content should be surfaced to the caller on escalation —
    # the frontend contract renders only the escalation message in this case.
    assert "answer" not in body
    assert "citations" not in body

    # The query_id must be a real row this request created, not a placeholder.
    query_id = uuid.UUID(body["query_id"])
    db = TestingSessionLocal()
    try:
        query = db.get(Query, query_id)
        assert query is not None
        assert query.status.value == "escalated"
        assert query.confidence_score == LOW_CONFIDENCE_RESULT["confidence_score"]

        draft = db.query(Draft).filter(Draft.query_id == query_id).one()
        assert draft.draft_text  # placeholder text, since answer_text was None
        assert draft.citations == []
    finally:
        db.close()
