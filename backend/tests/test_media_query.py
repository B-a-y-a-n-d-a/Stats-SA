"""Tests for specs/005-media-query-draft.

No Postgres needed: `get_db` is overridden with an in-memory session that
records the rows the endpoint writes, and `answer_query` is replaced with a
canned retrieval result. What's under test is the media path's contract — a
draft every time, an answer never — not 003's retrieval, which has its own
integration tests.
"""
import json
import uuid

import pytest
from fastapi.testclient import TestClient

from app.api import media_query
from app.db.models import Draft, Query, QueryChannel, QueryStatus
from app.db.session import get_db
from app.main import app
from app.retrieval.draft_builder import GAP_TONE, build_draft

CHUNK_ID = str(uuid.uuid4())

GROUNDED = {
    "answer_text": "Manufacturing output fell 0.2% in Q2 2026.",
    "citations": [
        {
            "chunk_id": CHUNK_ID,
            "source_id": str(uuid.uuid4()),
            "title": "GDP Fact Sheet A - Q2 2026",
            "url": "https://www.statssa.gov.za/publications/P0441/factsheetA.pdf",
            "quote": "Manufacturing contracted by 0.2% and shed 12 thousand jobs.",
        }
    ],
    "confidence_score": 0.52,
    "above_threshold": True,
}

NO_EVIDENCE = {"answer_text": None, "citations": [], "confidence_score": 0.0, "above_threshold": False}

SUBMISSION = {
    "text": "How did manufacturing output move in Q2 2026?",
    "submitter_name": "Thandi Nkosi",
    "submitter_org": "Daily Maverick",
    "submitter_email": "thandi@example.com",
}


class FakeSession:
    def __init__(self):
        self.added = []
        self.committed = False

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        for obj in self.added:
            if isinstance(obj, Query) and obj.query_id is None:
                obj.query_id = uuid.uuid4()

    def commit(self):
        self.committed = True

    def rows(self, model):
        return [o for o in self.added if isinstance(o, model)]


@pytest.fixture
def db():
    session = FakeSession()
    # app.dependency_overrides is a single dict shared by the whole app, and
    # test_public_query.py sets its own get_db override at module-import time
    # (not inside a fixture) — a blanket .clear() here would silently wipe
    # that out too and leave later tests in other files hitting the real
    # Postgres instead of their intended fake/in-memory session. Save and
    # restore only the key this fixture itself touches.
    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = lambda: session
    yield session
    if previous is not None:
        app.dependency_overrides[get_db] = previous
    else:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client(db):
    return TestClient(app)


def _stub_retrieval(monkeypatch, result):
    monkeypatch.setattr(media_query, "answer_query", lambda db, text: result)


@pytest.mark.parametrize("result", [GROUNDED, NO_EVIDENCE])
def test_every_submission_creates_a_draft_and_returns_no_answer(client, db, monkeypatch, result):
    _stub_retrieval(monkeypatch, result)

    response = client.post("/api/media/query", json=SUBMISSION)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == QueryStatus.escalated.value
    assert body["message"] == media_query.CONFIRMATION
    # The submitter is never handed an answer, a draft or citations.
    assert set(body) == {"query_id", "status", "message"}

    query = db.rows(Query)[0]
    assert query.channel is QueryChannel.media
    assert query.status is QueryStatus.escalated
    draft = db.rows(Draft)[0]
    assert draft.query_id == query.query_id
    assert db.committed


def test_draft_records_submitter_and_structured_fields(client, db, monkeypatch):
    _stub_retrieval(monkeypatch, GROUNDED)

    client.post("/api/media/query", json=SUBMISSION)

    draft = json.loads(db.rows(Draft)[0].draft_text)
    assert draft["submitter"]["org"] == "Daily Maverick"
    assert draft["headline"] == SUBMISSION["text"]
    assert draft["body"] == GROUNDED["answer_text"]
    assert draft["information_gap"] is False
    assert [f["figure"] for f in draft["key_figures"]] == [
        "Manufacturing contracted by 0.2% and shed 12 thousand jobs"
    ]


def test_low_confidence_still_escalates_instead_of_answering(client, db, monkeypatch):
    # A grounded answer that sits under the confidence threshold is a draft too,
    # just a more cautious one — `above_threshold` never gates the media path.
    _stub_retrieval(monkeypatch, {**GROUNDED, "confidence_score": 0.21, "above_threshold": False})

    response = client.post("/api/media/query", json=SUBMISSION)

    assert response.status_code == 201
    assert len(db.rows(Draft)) == 1
    assert json.loads(db.rows(Draft)[0].draft_text)["suggested_tone"].startswith("cautious")


def test_draft_without_sources_states_the_gap_rather_than_inventing(client, db, monkeypatch):
    _stub_retrieval(monkeypatch, NO_EVIDENCE)

    client.post("/api/media/query", json=SUBMISSION)

    draft = json.loads(db.rows(Draft)[0].draft_text)
    assert draft["information_gap"] is True
    assert draft["key_figures"] == []
    assert draft["citations"] == []
    assert draft["suggested_tone"] == GAP_TONE
    assert "does not currently contain enough material" in draft["body"]


def test_submitter_details_are_required(client, monkeypatch):
    _stub_retrieval(monkeypatch, GROUNDED)

    response = client.post("/api/media/query", json={"text": "Q2 GDP?"})

    assert response.status_code == 422


def test_key_figures_only_come_from_enforced_citation_quotes():
    # The answer text claims 45%; no citation quote contains it, so it must not
    # surface as a key figure the reviewer could mistake for a sourced number.
    result = {
        "answer_text": "Unemployment reached 45%.",
        "citations": [{**GROUNDED["citations"][0], "quote": "the rate stood at 32.9% in Q2"}],
        "confidence_score": 0.5,
        "above_threshold": True,
    }

    draft = build_draft("What is unemployment?", result)

    assert [f["figure"] for f in draft["key_figures"]] == ["the rate stood at 32.9% in Q2"]
