"""Tests for app.core.audit.log_event and GET /api/audit (specs/010-audit-log/spec.md).

Runs FastAPI's TestClient against the real app (app.main.app), with get_db overridden
to an in-memory SQLite engine (StaticPool, check_same_thread=False — the same pattern
tests/test_public_query.py already uses successfully), creating only the `audit_log`
table via Base.metadata.create_all(..., tables=[...]). audit_log's FKs to users/queries/
sources are all nullable and this suite never relies on the DB enforcing them, so those
tables are never created here (same reasoning test_public_query.py documents for its
own FK to `users`).

log_event() opens its own short-lived session via app.core.audit.SessionLocal rather
than accepting one from the caller (callers like app/api/public_query.py call it with
no `db` argument at all). To exercise it against this suite's in-memory DB instead of
the real Postgres one, tests that call log_event() directly patch
`app.core.audit.SessionLocal` to this file's TestingSessionLocal for the duration of
the call.

An autouse fixture re-applies this file's get_db override immediately before each test
and clears the audit_log table. That override and test_public_query.py's both mutate
the same shared `app.dependency_overrides` dict — whichever module pytest imports last
during collection would otherwise "win" for every test in the session regardless of file
order, so re-asserting it per-test here keeps this file correct no matter how the full
suite is invoked.
"""
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.audit import log_event
from app.core.security import create_access_token
from app.db.models import AuditLog
from app.db.session import Base, get_db
from app.main import app

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # keeps the single in-memory DB alive across connections/sessions
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base.metadata.create_all(bind=engine, tables=[AuditLog.__table__])


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _audit_test_db():
    # Restore whatever get_db override (if any) was in place before this test, rather
    # than unconditionally clearing it — other test modules (e.g. test_public_query.py)
    # install their own override on this same shared `app` object at import time, and
    # popping the key outright here would leave it unset for whichever module's tests
    # run after this file's, regardless of collection order.
    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = _override_get_db
    db = TestingSessionLocal()
    try:
        db.query(AuditLog).delete()
        db.commit()
    finally:
        db.close()
    yield
    if previous_override is not None:
        app.dependency_overrides[get_db] = previous_override
    else:
        app.dependency_overrides.pop(get_db, None)


client = TestClient(app)


def _auth_header(role: str) -> dict:
    token = create_access_token(user_id=str(uuid.uuid4()), role=role)
    return {"Authorization": f"Bearer {token}"}


COMMS_OFFICIAL = _auth_header("comms_official")
CURATOR_ADMIN = _auth_header("curator_admin")
PUBLIC = _auth_header("public")
MEDIA = _auth_header("media")


# --- log_event() -------------------------------------------------------------------


def test_log_event_writes_a_retrievable_row():
    query_id = uuid.uuid4()

    with patch("app.core.audit.SessionLocal", TestingSessionLocal):
        log_event("query_submitted", query_id=query_id, payload={"channel": "public"})

    db = TestingSessionLocal()
    try:
        rows = db.query(AuditLog).filter(AuditLog.event_type == "query_submitted").all()
        assert len(rows) == 1
        row = rows[0]
        assert row.query_id == query_id
        assert row.payload == {"channel": "public"}
        assert row.actor_id is None
        assert row.source_id is None
        assert row.sla_status is None
        assert row.created_at is not None
    finally:
        db.close()


def test_log_event_never_raises_when_the_session_factory_is_broken(capsys):
    broken_session_factory = MagicMock(side_effect=RuntimeError("db is unreachable"))

    with patch("app.core.audit.SessionLocal", broken_session_factory):
        log_event("query_submitted", query_id=uuid.uuid4())  # must not raise

    assert "WARNING" in capsys.readouterr().err


def test_log_event_never_raises_when_commit_fails(capsys):
    broken_session = MagicMock()
    broken_session.commit.side_effect = RuntimeError("commit failed")

    with patch("app.core.audit.SessionLocal", MagicMock(return_value=broken_session)):
        log_event("answer_generated", query_id=uuid.uuid4())  # must not raise

    assert "WARNING" in capsys.readouterr().err
    broken_session.close.assert_called_once()


# --- GET /api/audit — access control ------------------------------------------------


def test_get_audit_without_token_returns_401():
    response = client.get("/api/audit")
    assert response.status_code == 401


def test_get_audit_with_public_role_returns_403():
    response = client.get("/api/audit", headers=PUBLIC)
    assert response.status_code == 403


def test_get_audit_with_media_role_returns_403():
    response = client.get("/api/audit", headers=MEDIA)
    assert response.status_code == 403


def test_get_audit_with_comms_official_returns_200_with_expected_shape():
    db = TestingSessionLocal()
    try:
        db.add(AuditLog(event_type="query_submitted", payload={"channel": "public"}))
        db.commit()
    finally:
        db.close()

    response = client.get("/api/audit", headers=COMMS_OFFICIAL)

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 1
    entry = body[0]
    assert set(entry.keys()) == {
        "log_id",
        "event_type",
        "actor_id",
        "query_id",
        "source_id",
        "payload",
        "sla_status",
        "created_at",
    }
    uuid.UUID(entry["log_id"])  # raises if not a valid UUID string
    assert entry["event_type"] == "query_submitted"
    assert entry["payload"] == {"channel": "public"}
    assert entry["actor_id"] is None
    assert entry["query_id"] is None
    assert entry["source_id"] is None
    assert entry["sla_status"] is None
    assert isinstance(entry["created_at"], str)


def test_get_audit_with_curator_admin_returns_200():
    response = client.get("/api/audit", headers=CURATOR_ADMIN)
    assert response.status_code == 200


# --- GET /api/audit — filtering and ordering ----------------------------------------


def test_query_id_filter_returns_only_matching_rows():
    target_query_id = uuid.uuid4()
    other_query_id = uuid.uuid4()
    db = TestingSessionLocal()
    try:
        db.add_all(
            [
                AuditLog(event_type="query_submitted", query_id=target_query_id),
                AuditLog(event_type="answer_generated", query_id=target_query_id),
                AuditLog(event_type="query_submitted", query_id=other_query_id),
            ]
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/api/audit", params={"query_id": str(target_query_id)}, headers=COMMS_OFFICIAL)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert {entry["query_id"] for entry in body} == {str(target_query_id)}


def test_invalid_query_id_returns_400():
    response = client.get("/api/audit", params={"query_id": "not-a-uuid"}, headers=COMMS_OFFICIAL)
    assert response.status_code == 400


def test_results_are_ordered_newest_first():
    db = TestingSessionLocal()
    try:
        older = AuditLog(event_type="query_submitted", created_at=datetime(2026, 1, 1))
        newer = AuditLog(event_type="answer_generated", created_at=datetime(2026, 6, 1))
        db.add_all([older, newer])
        db.commit()
    finally:
        db.close()

    response = client.get("/api/audit", headers=COMMS_OFFICIAL)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["event_type"] == "answer_generated"
    assert body[1]["event_type"] == "query_submitted"


def test_date_range_filter_is_inclusive_and_excludes_outside_rows():
    db = TestingSessionLocal()
    try:
        db.add_all(
            [
                AuditLog(event_type="before_range", created_at=datetime(2026, 1, 1)),
                AuditLog(event_type="in_range_start", created_at=datetime(2026, 2, 1)),
                AuditLog(event_type="in_range_end", created_at=datetime(2026, 2, 28)),
                AuditLog(event_type="after_range", created_at=datetime(2026, 3, 15)),
            ]
        )
        db.commit()
    finally:
        db.close()

    response = client.get(
        "/api/audit",
        params={"start_date": "2026-02-01", "end_date": "2026-02-28"},
        headers=COMMS_OFFICIAL,
    )

    assert response.status_code == 200
    event_types = {entry["event_type"] for entry in response.json()}
    assert event_types == {"in_range_start", "in_range_end"}
