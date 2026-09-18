"""Integration tests for retrieval + confidence gate + citation enforcement,
run against the real Postgres container (docker-compose up -d db). Uses a
fake LLM client so no API key is needed — the acceptance criteria this task
cares about are the confidence-gate and citation-enforcement mechanism, not
the specific vendor call (app/retrieval/llm_client.py has the real Anthropic
wiring, not exercised here — no key is available in this build environment).
specs/003-retrieval-confidence-gate/spec.md.
"""
import datetime
import json
from pathlib import Path

import pytest

from app.core.config import settings
from app.db.models import Chunk, Source, SourceCategory
from app.db.session import SessionLocal
from app.ingestion.service import ingest_source
from app.retrieval.llm_client import LLMClient
from app.retrieval.service import answer_query

FIXTURE = Path(__file__).parent / "fixtures" / "P0441_factsheetA.pdf"
TEST_URL = "https://www.statssa.gov.za/publications/P0441/Fact sheet A - Q2 2026.pdf"


class FakeLLMClient(LLMClient):
    def __init__(self, response: dict):
        self.response = response

    def generate(self, system_prompt, user_prompt):
        return json.dumps(self.response)


@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    session.query(Chunk).delete()
    session.query(Source).delete()
    session.commit()

    data = FIXTURE.read_bytes()
    ingest_source(
        session,
        file_bytes=data,
        title="GDP Fact Sheet A - Q2 2026",
        url=TEST_URL,
        category=SourceCategory.press_statement,
        published_date=datetime.date(2026, 9, 8),
    )
    yield session
    session.close()


def _first_chunk(db):
    return db.query(Chunk).first()


def test_high_confidence_returns_grounded_answer_with_citation(db):
    chunk = _first_chunk(db)
    quote = chunk.text.strip().split("\n")[0][:40]

    fake_llm = FakeLLMClient(
        {"answer": "GDP fell 0.2% in Q2 2026.", "citations": [{"chunk_id": str(chunk.chunk_id), "quote": quote}]}
    )
    result = answer_query(db, "How did GDP change in the manufacturing industry in Q2 2026?", llm_client=fake_llm)

    assert result["answer_text"] == "GDP fell 0.2% in Q2 2026."
    assert result["confidence_score"] >= settings.confidence_threshold
    assert result["above_threshold"] is True
    assert len(result["citations"]) == 1
    assert result["citations"][0]["chunk_id"] == str(chunk.chunk_id)


def test_hallucinated_citation_is_dropped_not_shown(db):
    # Model cites a chunk_id that was never retrieved for this query at all —
    # enforcement must reject it structurally, not display it.
    fake_llm = FakeLLMClient(
        {
            "answer": "Unemployment reached 45%.",
            "citations": [{"chunk_id": "00000000-0000-0000-0000-000000000000", "quote": "made up"}],
        }
    )
    result = answer_query(db, "manufacturing industry growth", llm_client=fake_llm)

    assert result["answer_text"] is None
    assert result["citations"] == []


def test_quote_not_actually_in_chunk_is_rejected(db):
    chunk = _first_chunk(db)
    fake_llm = FakeLLMClient(
        {
            "answer": "Something.",
            "citations": [{"chunk_id": str(chunk.chunk_id), "quote": "this exact sentence is not in the document"}],
        }
    )
    result = answer_query(db, "manufacturing industry growth", llm_client=fake_llm)

    assert result["answer_text"] is None
    assert result["citations"] == []


def test_low_confidence_query_does_not_clear_threshold(db):
    fake_llm = FakeLLMClient({"answer": None, "citations": []})
    result = answer_query(db, "completely unrelated topic: weather forecasting for coastal fishing towns", llm_client=fake_llm)

    assert result["confidence_score"] < settings.confidence_threshold
    assert result["above_threshold"] is False


def test_zero_match_registry_returns_no_fabricated_answer(db):
    # Empty registry entirely — the LLM must never even be asked.
    db.query(Chunk).delete()
    db.query(Source).delete()
    db.commit()

    fake_llm = FakeLLMClient({"answer": "Should never see this.", "citations": []})
    result = answer_query(db, "anything at all", llm_client=fake_llm)

    assert result["answer_text"] is None
    assert result["above_threshold"] is False
    assert result["confidence_score"] == 0.0
