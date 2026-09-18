"""Tests for specs/009-rbac-auth.

These run without Postgres: the login endpoint's `get_db` dependency is overridden
with an in-memory stand-in holding the same 4 demo accounts `app.db.seed` creates,
so the JWT and role logic is exercised end-to-end through the real HTTP layer.
"""
import uuid

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.passwords import hash_password
from app.core.security import create_access_token, require_role
from app.db.models import User, UserRole
from app.db.seed import DEMO_ACCOUNTS, DEMO_PASSWORD
from app.db.session import get_db
from app.main import app


class FakeQuery:
    def __init__(self, users):
        self._users = users
        self._email = None

    def filter(self, criterion):
        self._email = criterion.right.value
        return self

    def first(self):
        return next((u for u in self._users if u.email == self._email), None)


class FakeSession:
    def __init__(self, users):
        self._users = users

    def query(self, model):
        assert model is User
        return FakeQuery(self._users)


@pytest.fixture(scope="module")
def demo_users():
    password_hash = hash_password(DEMO_PASSWORD)
    return [
        User(user_id=uuid.uuid4(), name=name, email=email, role=role, password_hash=password_hash)
        for name, email, role in DEMO_ACCOUNTS
    ]


@pytest.fixture
def client(demo_users):
    app.dependency_overrides[get_db] = lambda: FakeSession(demo_users)
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.mark.parametrize("name,email,role", DEMO_ACCOUNTS)
def test_login_returns_jwt_with_correct_role(client, name, email, role):
    response = client.post("/api/auth/login", json={"email": email, "password": DEMO_PASSWORD})

    assert response.status_code == 200
    body = response.json()
    assert body["role"] == role.value
    assert body["token_type"] == "bearer"

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json() == {"user_id": body["user_id"], "role": role.value}


def test_login_rejects_wrong_password(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "curator@demo.statssa.local", "password": "not-the-password"},
    )
    assert response.status_code == 401


def test_login_rejects_unknown_email(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "nobody@demo.statssa.local", "password": DEMO_PASSWORD},
    )
    assert response.status_code == 401


@pytest.fixture
def protected_client():
    protected = FastAPI()

    @protected.get("/curator-only")
    def curator_only(user=Depends(require_role("curator_admin"))):
        return {"user_id": user.user_id}

    @protected.get("/reviewer-or-curator")
    def reviewer_or_curator(user=Depends(require_role(UserRole.comms_official, UserRole.curator_admin))):
        return {"role": user.role.value}

    return TestClient(protected)


def _auth(role: UserRole) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(uuid.uuid4()), role)}"}


@pytest.mark.parametrize("role", [UserRole.public, UserRole.media, UserRole.comms_official])
def test_require_role_rejects_other_roles_with_403(protected_client, role):
    response = protected_client.get("/curator-only", headers=_auth(role))
    assert response.status_code == 403


def test_require_role_allows_matching_role(protected_client):
    assert protected_client.get("/curator-only", headers=_auth(UserRole.curator_admin)).status_code == 200


def test_require_role_accepts_any_listed_role(protected_client):
    for role in (UserRole.comms_official, UserRole.curator_admin):
        response = protected_client.get("/reviewer-or-curator", headers=_auth(role))
        assert response.status_code == 200
        assert response.json()["role"] == role.value


def test_missing_token_is_401(protected_client):
    assert protected_client.get("/curator-only").status_code == 401


def test_tampered_token_is_401(protected_client):
    token = create_access_token(str(uuid.uuid4()), UserRole.curator_admin)
    response = protected_client.get("/curator-only", headers={"Authorization": f"Bearer {token}x"})
    assert response.status_code == 401


def test_client_supplied_role_header_is_never_trusted(protected_client):
    response = protected_client.get(
        "/curator-only",
        headers={**_auth(UserRole.public), "X-Demo-Role": "curator_admin"},
    )
    assert response.status_code == 403
