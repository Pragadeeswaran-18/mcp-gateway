"""Tenant isolation. The first half needs no database; the second half needs MongoDB."""

import contextlib
import os
import uuid
from datetime import UTC, datetime

import pytest

from admin.models import ApprovalRequest, AuditEvent, ToolRule
from store.mongo import MongoStore
from store.orm import AppendOnlyError, check_filter, from_doc, scope_filter, to_doc
from store.tenant import TenantError, current_tenant, use_tenant, validate_tenant_id

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")


# --- pure unit tests -------------------------------------------------------------------


def test_scope_filter_wraps_and_cannot_be_widened():
    assert scope_filter("a", None) == {"tenant_id": "a"}
    assert scope_filter("a", {"x": 1}) == {"$and": [{"tenant_id": "a"}, {"x": 1}]}
    # an $or cannot escape: it sits inside the $and next to the tenant clause
    wrapped = scope_filter("a", {"$or": [{"x": 1}, {"y": 2}]})
    assert wrapped["$and"][0] == {"tenant_id": "a"}


@pytest.mark.parametrize(
    "bad",
    [
        {"tenant_id": "b"},
        {"_id": "b:x"},
        {"$or": [{"tenant_id": "b"}]},
        {"x": {"$in": [{"tenant_id": "b"}]}},
        {"$where": "true"},
    ],
)
def test_filters_naming_reserved_fields_are_rejected(bad):
    with pytest.raises(TenantError):
        check_filter(bad)


@pytest.mark.parametrize("bad", ["", "A", "a:b", "$x", "a b", "x" * 65, None])
def test_invalid_tenant_ids(bad):
    with pytest.raises(TenantError):
        validate_tenant_id(bad)


def test_tenant_context_fails_closed_and_resets():
    with pytest.raises(TenantError):
        current_tenant()
    with use_tenant("acme"):
        assert current_tenant() == "acme"
    with pytest.raises(TenantError):
        current_tenant()


def test_doc_roundtrip_namespaces_id_and_strips_tenant():
    rule = ToolRule(tool="send_message", allow=["alice"])
    doc = to_doc("acme", "send_message", rule)
    assert doc["_id"] == "acme:send_message" and doc["tenant_id"] == "acme"
    assert from_doc(ToolRule, doc) == rule


# --- MongoDB integration ----------------------------------------------------------------


@pytest.fixture
async def store():
    s = MongoStore(MONGO_URL, f"policy_gateway_test_{uuid.uuid4().hex[:8]}")
    try:
        yield s
    finally:
        with contextlib.suppress(Exception):  # nothing to clean up if MongoDB is unreachable
            await s._client.drop_database(s._tdb.db.name)
        await s.close()


async def test_same_key_in_two_tenants_is_isolated(store: MongoStore):
    await store.init()
    with use_tenant("a"):
        await store.put_rule(ToolRule(tool="t", allow=["alice"]))
    with use_tenant("b"):
        assert await store.list_rules() == []
        assert await store.get_rule("t") is None
        await store.put_rule(ToolRule(tool="t", deny=["bob"]))
        assert await store.delete_rule("t") is True
    with use_tenant("a"):
        assert (await store.get_rule("t")).allow == ["alice"]


async def test_approvals_cannot_be_resolved_across_tenants(store: MongoStore):
    req = ApprovalRequest(
        id="r1", human="alice", agent="ag", task_id="t", tool="x", created_at=datetime.now(UTC)
    )
    with use_tenant("a"):
        await store.create_approval(req)
    with use_tenant("b"):
        assert await store.resolve_approval("r1", True, "admin-b") is False
    with use_tenant("a"):
        assert (await store.list_approvals("pending"))[0].id == "r1"
        assert await store.resolve_approval("r1", True, "admin-a") is True


async def test_audit_is_tenant_scoped_and_append_only(store: MongoStore):
    event = AuditEvent(
        ts=datetime.now(UTC), human="alice", agent="ag", task_id="t", tool="x",
        decision="deny", rule="r",
    )  # fmt: skip
    with use_tenant("a"):
        await store.append_audit(event)
        assert len(await store.query_audit({})) == 1
        with pytest.raises(AppendOnlyError):
            await store._audit().delete("anything")
        with pytest.raises(TenantError):
            await store.query_audit({"tenant_id": "b"})
    with use_tenant("b"):
        assert await store.query_audit({}) == []


async def test_no_tenant_means_no_access(store: MongoStore):
    with pytest.raises(TenantError):
        await store.list_rules()
