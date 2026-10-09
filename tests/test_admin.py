"""Admin API scenarios. Need MongoDB (make mongo); fail until the admin server is built."""

import os
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

from admin.app import create_app
from store.mongo import MongoStore

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
ADMIN_TOKEN = "test-admin-token"
AUTH = {"Authorization": f"Bearer {ADMIN_TOKEN}"}

RULE = {
    "tool": "send_message",
    "allow": ["alice"],
    "pins": {"phone_number": {"value": "ref:USER_A_PHONE", "on_conflict": "reject"}},
    "constraints": {"message": {"reject_pattern": r"\d{9,}"}},
}


@pytest.fixture
def open_admin(monkeypatch: pytest.MonkeyPatch):
    """Factory for a client on a throwaway database (dropped on exit). Tests call it inside
    the test body so a missing implementation fails the test rather than erroring in setup."""
    monkeypatch.setenv("ADMIN_TOKEN", ADMIN_TOKEN)

    @contextmanager
    def _open() -> Iterator[TestClient]:
        db_name = f"policy_gateway_test_{uuid.uuid4().hex[:8]}"
        app = create_app(MongoStore(MONGO_URL, db_name))  # fails fast while stubbed
        try:
            with TestClient(app) as client:
                yield client
        finally:
            MongoClient(MONGO_URL, serverSelectionTimeoutMS=3000).drop_database(db_name)

    return _open


def test_admin_requires_admin_token(open_admin):
    with open_admin() as admin:
        assert admin.get("/rules").status_code == 401
        assert admin.get("/rules", headers={"Authorization": "Bearer wrong"}).status_code in (
            401,
            403,
        )
        assert admin.get("/rules", headers=AUTH).status_code == 200


def test_rule_crud_roundtrip(open_admin):
    with open_admin() as admin:
        assert admin.put("/rules/send_message", json=RULE, headers=AUTH).status_code == 200
        assert admin.get("/rules", headers=AUTH).json() == [
            {**RULE, "deny": [], "require_approval": []}
        ]
        assert admin.delete("/rules/send_message", headers=AUTH).status_code == 204
        assert admin.delete("/rules/send_message", headers=AUTH).status_code == 404
        assert admin.get("/rules", headers=AUTH).json() == []


def test_rule_validation(open_admin):
    with open_admin() as admin:
        bad_regex = {**RULE, "constraints": {"message": {"reject_pattern": "("}}}
        assert admin.put("/rules/send_message", json=bad_regex, headers=AUTH).status_code == 422
        mismatch = {**RULE, "tool": "other"}
        assert admin.put("/rules/send_message", json=mismatch, headers=AUTH).status_code == 422


def test_user_crud_roundtrip(open_admin):
    with open_admin() as admin:
        user = {"username": "alice", "active": True, "agent_ids": ["agent-alice"]}
        assert admin.put("/users/alice", json=user, headers=AUTH).status_code == 200
        assert admin.get("/users", headers=AUTH).json() == [user]
        assert admin.delete("/users/alice", headers=AUTH).status_code == 204


def test_unknown_approval_cannot_be_resolved(open_admin):
    with open_admin() as admin:
        assert admin.post("/approvals/nope/approve", headers=AUTH).status_code in (404, 409)
        assert admin.get("/approvals", headers=AUTH).json() == []


def test_audit_is_read_only(open_admin):
    with open_admin() as admin:
        assert admin.get("/audit", headers=AUTH).status_code == 200
        assert admin.post("/audit", json={}, headers=AUTH).status_code == 405
        assert admin.delete("/audit", headers=AUTH).status_code == 405
