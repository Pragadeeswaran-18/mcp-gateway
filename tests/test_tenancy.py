"""Tenant isolation. The first half needs no database; the second half needs MongoDB."""

from datetime import UTC, datetime

import httpx
import pytest

from admin.models import ApprovalRequest, AuditEvent, Tenant, ToolRule
from store.mongo import MongoStore
from store.orm import AppendOnlyError, check_filter, from_doc, scope_filter, to_doc
from store.registry import TenantRegistry
from store.resolve import TenantMiddleware, subdomain_from_host
from store.tenant import TenantError, current_tenant, use_tenant, validate_tenant_id

# --- pure unit tests -------------------------------------------------------------------


def test_scope_filter_wraps_and_cannot_be_widened():
    assert scope_filter(1, None) == {"tenant_id": 1}
    assert scope_filter(1, {"x": 1}) == {"$and": [{"tenant_id": 1}, {"x": 1}]}
    # an $or cannot escape: it sits inside the $and next to the tenant clause
    wrapped = scope_filter(1, {"$or": [{"x": 1}, {"y": 2}]})
    assert wrapped["$and"][0] == {"tenant_id": 1}


@pytest.mark.parametrize(
    "bad",
    [
        {"tenant_id": 2},
        {"_id": "b:x"},
        {"$or": [{"tenant_id": 2}]},
        {"x": {"$in": [{"tenant_id": 2}]}},
        {"$where": "true"},
    ],
)
def test_filters_naming_reserved_fields_are_rejected(bad):
    with pytest.raises(TenantError):
        check_filter(bad)


@pytest.mark.parametrize("bad", [0, -1, "1", "acme", True, 1.5, None])
def test_invalid_tenant_ids(bad):
    with pytest.raises(TenantError):
        validate_tenant_id(bad)


def test_tenant_context_fails_closed_and_resets():
    with pytest.raises(TenantError):
        current_tenant()
    with use_tenant(7):
        assert current_tenant() == 7
    with pytest.raises(TenantError):
        current_tenant()


def test_doc_roundtrip_namespaces_id_and_strips_tenant():
    rule = ToolRule(tool="send_message", allow=["alice"])
    doc = to_doc(7, "send_message", rule)
    assert doc["_id"] == "7:send_message" and doc["tenant_id"] == 7
    assert from_doc(ToolRule, doc) == rule


# --- MongoDB integration ----------------------------------------------------------------


async def test_same_key_in_two_tenants_is_isolated(store: MongoStore):
    await store.init()
    with use_tenant(1):
        await store.put_rule(ToolRule(tool="t", allow=["alice"]))
    with use_tenant(2):
        assert await store.list_rules() == []
        assert await store.get_rule("t") is None
        await store.put_rule(ToolRule(tool="t", deny=["bob"]))
        assert await store.delete_rule("t") is True
    with use_tenant(1):
        assert (await store.get_rule("t")).allow == ["alice"]


async def test_approvals_cannot_be_resolved_across_tenants(store: MongoStore):
    req = ApprovalRequest(
        id="r1", human="alice", agent="ag", task_id="t", tool="x", created_at=datetime.now(UTC)
    )
    with use_tenant(1):
        await store.create_approval(req)
    with use_tenant(2):
        assert await store.resolve_approval("r1", True, "admin-b") is False
    with use_tenant(1):
        assert (await store.list_approvals("pending"))[0].id == "r1"
        assert await store.resolve_approval("r1", True, "admin-a") is True


async def test_audit_is_tenant_scoped_and_append_only(store: MongoStore):
    event = AuditEvent(
        ts=datetime.now(UTC), human="alice", agent="ag", task_id="t", tool="x",
        decision="deny", rule="r",
    )  # fmt: skip
    with use_tenant(1):
        await store.append_audit(event)
        assert len(await store.query_audit({})) == 1
        with pytest.raises(AppendOnlyError):
            await store._audit().delete("anything")
        with pytest.raises(TenantError):
            await store.query_audit({"tenant_id": 2})
    with use_tenant(2):
        assert await store.query_audit({}) == []


async def test_no_tenant_means_no_access(store: MongoStore):
    with pytest.raises(TenantError):
        await store.list_rules()


# --- subdomain resolution ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("acme.gw.example.com", "acme"),
        ("ACME.gw.example.com:8080", "acme"),
        ("acme.gw.example.com.", "acme"),
        ("gw.example.com", None),  # bare base domain
        ("a.b.gw.example.com", None),  # nested
        ("acme.other.com", None),
        ("evilgw.example.com", None),  # suffix without the dot boundary
        ("-x.gw.example.com", None),
        ("", None),
    ],
)
def test_subdomain_from_host(host, expected):
    assert subdomain_from_host(host, "gw.example.com") == expected


class _FakeRegistry:
    def __init__(self, tenants):
        self._by_sub = {t.subdomain: t for t in tenants}

    async def get_by_subdomain(self, subdomain):
        return self._by_sub.get(subdomain)


async def test_middleware_sets_numeric_tenant_from_host():
    async def app(scope, receive, send):
        body = str(current_tenant()).encode()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": body})

    registry = _FakeRegistry(
        [Tenant(tenant_id=7, subdomain="acme"), Tenant(tenant_id=9, subdomain="off", active=False)]
    )
    transport = httpx.ASGITransport(app=TenantMiddleware(app, registry, "gw.example.com"))
    async with httpx.AsyncClient(transport=transport) as client:
        ok = await client.get("http://acme.gw.example.com/x")
        assert (ok.status_code, ok.text) == (200, "7")
        for host in ("nope.gw.example.com", "off.gw.example.com", "gw.example.com"):
            assert (await client.get(f"http://{host}/x")).status_code == 404
    with pytest.raises(TenantError):  # context does not leak past the request
        current_tenant()


async def test_registry_allocates_numeric_ids(store: MongoStore):
    registry = TenantRegistry(store._tdb.db)
    await registry.init()
    a = await registry.create("acme")
    b = await registry.create("globex")
    assert (a.tenant_id, b.tenant_id) == (1, 2)
    assert (await registry.get_by_subdomain("globex")).tenant_id == 2
    with pytest.raises(TenantError):
        await registry.create("acme")
