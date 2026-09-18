"""Tests for app/api/curator.py (specs/008-curator-admin/spec.md), branch
feature/008-curator-admin.

Runs FastAPI's TestClient against the real app (app.main.app), with get_db
overridden to an in-memory SQLite engine (StaticPool, check_same_thread=False —
the same pattern tests/test_audit.py and tests/test_review.py already use
successfully).

Base.metadata.create_all(...) creates Source, TerminologyGuide and User —
plus two additions beyond that minimal set, both deliberate:

  * Chunk.__table__ — POST /api/curator/sources exercises the real
    app.ingestion.service.ingest_source() end to end (per this task's
    instructions), which inserts Chunk rows as part of ingesting the PDF
    fixture. Chunk.embedding is a pgvector Vector column, which sounds
    postgres-only, but pgvector-python's SQLAlchemy Vector type is a plain
    UserDefinedType whose bind/result processors just (de)serialize a Python
    list to/from a string — verified directly against this suite's SQLite
    engine before relying on it here. No real pgvector extension, and no
    vector similarity operator (only search.py's search_chunks() needs
    those), is required for plain insert/select, so this works without a
    real Postgres+pgvector instance.
  * AuditLog.__table__ — every mutating endpoint here calls
    app.core.audit.log_event(...) after committing. log_event() opens its
    own session via its module-level SessionLocal (see app/core/audit.py)
    rather than accepting one from the caller, so — same as test_audit.py
    and test_review.py — an autouse fixture below patches
    `app.core.audit.SessionLocal` to this file's TestingSessionLocal for the
    duration of each test. Without the table, that write would just be
    silently swallowed by log_event's broad except (by design, per specs/010)
    rather than actually failing a test — but creating the table lets it
    land for real instead of falling through to a real, almost certainly
    unreachable, production Postgres URL on every single test.

An autouse fixture re-applies this file's get_db override immediately before
each test and clears its tables. That override and the other test modules'
overrides all mutate the same shared `app.dependency_overrides` dict —
whichever module pytest imports/runs last would otherwise "win" for the whole
session regardless of file order, so this fixture saves and restores only the
one key it touches rather than ever calling app.dependency_overrides.clear()
(that exact blanket-clear bug already hit two other PRs in this project — see
the test_audit.py module docstring).

Auth uses real JWTs via app.core.security.create_access_token. Every endpoint
here is gated to curator_admin only (no second allowed role, unlike
app/api/audit.py) — each endpoint gets its own 403-for-non-curator_admin test
using the "public" role.

The httpx-fetch-by-URL branch of POST /api/curator/sources (no `file` in the
form) is intentionally not covered here — it needs real network access, and
per this task's instructions is verified live separately.
"""
import uuid
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db.models import AuditLog, Chunk, Source, TerminologyGuide, User
from app.db.session import Base, get_db
from app.main import app

FIXTURE_PDF = Path(__file__).parent / "fixtures" / "P0441_factsheetA.pdf"

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # keeps the single in-memory DB alive across connections/sessions
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base.metadata.create_all(
    bind=engine,
    tables=[Source.__table__, TerminologyGuide.__table__, User.__table__, Chunk.__table__, AuditLog.__table__],
)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _curator_test_db():
    # Save/restore only this fixture's own key — never a blanket
    # app.dependency_overrides.clear() (see module docstring).
    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = _override_get_db
    db = TestingSessionLocal()
    try:
        db.query(Chunk).delete()
        db.query(Source).delete()
        db.query(TerminologyGuide).delete()
        db.query(User).delete()
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


CURATOR_ADMIN_ID = str(uuid.uuid4())
CURATOR_ADMIN = _auth_header("curator_admin", CURATOR_ADMIN_ID)
PUBLIC = _auth_header("public")
COMMS_OFFICIAL = _auth_header("comms_official")
MEDIA = _auth_header("media")


def _upload_source(headers: dict, **overrides) -> "TestClient.Response":  # type: ignore[name-defined]
    data = {
        "title": "GDP Fact Sheet",
        "url": "https://www.statssa.gov.za/publications/P0441/factsheetA.pdf",
        "category": "FAQ",
        "published_date": "2026-01-15",
    }
    data.update(overrides)
    files = {"file": ("test.pdf", FIXTURE_PDF.read_bytes(), "application/pdf")}
    return client.post("/api/curator/sources", data=data, files=files, headers=headers)


def _terminology_payload(**overrides) -> dict:
    payload = {
        "category": "Terminology",
        "term_or_topic": "Unemployment rate",
        "approved_guidance": "Use 'official unemployment rate' and cite the QLFS release.",
        "discouraged_alternative": "jobless rate",
        "rationale": "Matches Stats SA's published methodology terminology.",
    }
    payload.update(overrides)
    return payload


# --- access control: every endpoint is curator_admin-only ---------------------------


def test_post_sources_as_public_returns_403():
    response = _upload_source(PUBLIC)
    assert response.status_code == 403


def test_post_sources_as_comms_official_returns_403():
    response = _upload_source(COMMS_OFFICIAL)
    assert response.status_code == 403


def test_get_sources_as_public_returns_403():
    response = client.get("/api/curator/sources", headers=PUBLIC)
    assert response.status_code == 403


def test_delete_source_as_public_returns_403():
    response = client.delete(f"/api/curator/sources/{uuid.uuid4()}", headers=PUBLIC)
    assert response.status_code == 403


def test_get_terminology_as_public_returns_403():
    response = client.get("/api/curator/terminology", headers=PUBLIC)
    assert response.status_code == 403


def test_post_terminology_as_public_returns_403():
    response = client.post("/api/curator/terminology", json=_terminology_payload(), headers=PUBLIC)
    assert response.status_code == 403


def test_post_sources_as_media_returns_403():
    response = _upload_source(MEDIA)
    assert response.status_code == 403


# --- POST /api/curator/sources -------------------------------------------------------


def test_upload_source_returns_200_with_source_id_and_version_1():
    response = _upload_source(CURATOR_ADMIN)

    assert response.status_code == 200
    body = response.json()
    uuid.UUID(body["source_id"])  # raises if not a valid UUID string
    assert body["version"] == 1
    assert body["title"] == "GDP Fact Sheet"

    db = TestingSessionLocal()
    try:
        source = db.get(Source, uuid.UUID(body["source_id"]))
        assert source is not None
        assert source.checksum
        assert str(source.approved_by) == CURATOR_ADMIN_ID

        logs = db.query(AuditLog).filter(AuditLog.event_type == "source_ingested").all()
        assert len(logs) == 1
        assert str(logs[0].actor_id) == CURATOR_ADMIN_ID
        assert logs[0].source_id == source.source_id
        assert logs[0].payload["version"] == 1
    finally:
        db.close()


def test_upload_non_pdf_content_returns_400_not_500():
    # Found live against a real statssa.gov.za URL: a site's bot-protection layer
    # (Incapsula) returned a 200 HTML challenge page instead of the PDF, which
    # previously reached pdfplumber unvalidated and 500'd with a raw stack trace.
    # A directly-uploaded non-PDF file must be caught the same way.
    response = client.post(
        "/api/curator/sources",
        data={
            "title": "Not a PDF",
            "url": "https://example.com/not-a-pdf",
            "category": "FAQ",
            "published_date": "2026-01-15",
        },
        files={"file": ("fake.pdf", b"<html>not a pdf</html>", "application/pdf")},
        headers=CURATOR_ADMIN,
    )
    assert response.status_code == 400


# --- GET /api/curator/sources ---------------------------------------------------------


def test_get_sources_includes_uploaded_source():
    upload = _upload_source(CURATOR_ADMIN)
    source_id = upload.json()["source_id"]

    response = client.get("/api/curator/sources", headers=CURATOR_ADMIN)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    entry = body[0]
    assert entry["source_id"] == source_id
    assert entry["title"] == "GDP Fact Sheet"
    assert entry["category"] == "FAQ"
    assert entry["version"] == 1
    assert entry["superseded_by"] is None
    assert entry["retired_at"] is None
    assert entry["confidentiality_tag"] == "Public"
    assert set(entry.keys()) == {
        "source_id",
        "title",
        "url",
        "category",
        "published_date",
        "ingested_date",
        "version",
        "superseded_by",
        "retired_at",
        "confidentiality_tag",
    }


# --- DELETE /api/curator/sources/{id} -------------------------------------------------


def test_delete_source_retires_it_and_is_idempotent():
    upload = _upload_source(CURATOR_ADMIN)
    source_id = upload.json()["source_id"]

    first = client.delete(f"/api/curator/sources/{source_id}", headers=CURATOR_ADMIN)
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["source_id"] == source_id
    assert first_body["retired_at"] is not None

    db = TestingSessionLocal()
    try:
        source = db.get(Source, uuid.UUID(source_id))
        assert source.retired_at is not None

        logs = db.query(AuditLog).filter(AuditLog.event_type == "source_retired").all()
        assert len(logs) == 1
        assert str(logs[0].actor_id) == CURATOR_ADMIN_ID
    finally:
        db.close()

    # Second DELETE is idempotent: still 200, same retired_at, no duplicate audit event.
    second = client.delete(f"/api/curator/sources/{source_id}", headers=CURATOR_ADMIN)
    assert second.status_code == 200
    assert second.json()["retired_at"] == first_body["retired_at"]

    db = TestingSessionLocal()
    try:
        logs = db.query(AuditLog).filter(AuditLog.event_type == "source_retired").all()
        assert len(logs) == 1
    finally:
        db.close()


def test_delete_unknown_source_returns_404():
    response = client.delete(f"/api/curator/sources/{uuid.uuid4()}", headers=CURATOR_ADMIN)
    assert response.status_code == 404


def test_delete_malformed_source_id_returns_404():
    response = client.delete("/api/curator/sources/not-a-uuid", headers=CURATOR_ADMIN)
    assert response.status_code == 404


# --- POST /api/curator/terminology ----------------------------------------------------


def test_create_terminology_entry():
    response = client.post("/api/curator/terminology", json=_terminology_payload(), headers=CURATOR_ADMIN)

    assert response.status_code == 200
    body = response.json()
    uuid.UUID(body["guide_entry_id"])
    assert body["term_or_topic"] == "Unemployment rate"
    assert body["category"] == "Terminology"
    assert body["version"] == 1
    assert body["superseded_by"] is None
    assert body["approved_by"] == CURATOR_ADMIN_ID
    assert body["effective_date"] == date.today().isoformat()
    assert body["last_reviewed_date"] is None

    db = TestingSessionLocal()
    try:
        logs = db.query(AuditLog).filter(AuditLog.event_type == "terminology_entry_created").all()
        assert len(logs) == 1
        assert logs[0].payload == {"term_or_topic": "Unemployment rate", "version": 1}
    finally:
        db.close()


def test_second_post_with_same_term_supersedes_the_first():
    first = client.post("/api/curator/terminology", json=_terminology_payload(), headers=CURATOR_ADMIN)
    first_id = first.json()["guide_entry_id"]

    second = client.post(
        "/api/curator/terminology",
        json=_terminology_payload(approved_guidance="Use 'official unemployment rate', per the revised QLFS."),
        headers=CURATOR_ADMIN,
    )

    assert second.status_code == 200
    second_body = second.json()
    assert second_body["version"] == 2
    assert second_body["guide_entry_id"] != first_id

    db = TestingSessionLocal()
    try:
        old_entry = db.get(TerminologyGuide, uuid.UUID(first_id))
        assert str(old_entry.superseded_by) == second_body["guide_entry_id"]
    finally:
        db.close()


# --- GET /api/curator/terminology -----------------------------------------------------


def test_get_terminology_lists_both_versions():
    first = client.post("/api/curator/terminology", json=_terminology_payload(), headers=CURATOR_ADMIN)
    first_id = first.json()["guide_entry_id"]
    second = client.post(
        "/api/curator/terminology",
        json=_terminology_payload(approved_guidance="Updated guidance."),
        headers=CURATOR_ADMIN,
    )
    second_id = second.json()["guide_entry_id"]

    response = client.get("/api/curator/terminology", headers=CURATOR_ADMIN)

    assert response.status_code == 200
    body = response.json()
    assert {entry["guide_entry_id"] for entry in body} == {first_id, second_id}
    by_id = {entry["guide_entry_id"]: entry for entry in body}
    assert by_id[first_id]["superseded_by"] == second_id
    assert by_id[first_id]["version"] == 1
    assert by_id[second_id]["superseded_by"] is None
    assert by_id[second_id]["version"] == 2
