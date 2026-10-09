"""Admin API scenarios (need MongoDB). Unbuilt endpoints fail with NotImplementedError."""

import httpx
import pytest
from httpx import ASGITransport

from admin.app import create_app
from common.models import User
from common.store.mongo import MongoStore
from common.store.tenant import use_tenant

ADMIN_TOKEN = "test-admin-token"
AUTH = {"Authorization": f"Bearer {ADMIN_TOKEN}"}

RULE = {
    "tool": "send_message",
    "allow": ["alice"],
    "pins": {"phone_number": {"value": "ref:USER_A_PHONE", "on_conflict": "reject"}},
    "constraints": {"message": {"reject_pattern": r"\d{9,}"}},
}


@pytest.fixture
async def app(store: MongoStore, monkeypatch: pytest.MonkeyPatch):
    """Admin app on a throwaway database with its lifespan running."""
    monkeypatch.setenv("ADMIN_TOKEN", ADMIN_TOKEN)
    monkeypatch.setenv("BASE_DOMAIN", "localhost")
    app = create_app(store)
    async with app.router.lifespan_context(app):
        yield app


def client(app, subdomain: str = "acme") -> httpx.AsyncClient:
    """Client whose Host header selects the tenant, as a browser would."""
    return httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url=f"http://{subdomain}.localhost"
    )


async def test_list_users_returns_only_this_tenants_users(app, store: MongoStore):
    registry = store.tenant_registry()
    acme = await registry.create("acme")
    globex = await registry.create("globex")
    with use_tenant(acme.tenant_id):
        await store.put_user(User(username="bob"))
        await store.put_user(User(username="alice", agent_ids=["agent-alice"]))
    with use_tenant(globex.tenant_id):
        await store.put_user(User(username="carol"))

    async with client(app, "acme") as c:
        res = await c.get("/users", headers=AUTH)
    assert res.status_code == 200
    assert [u["username"] for u in res.json()] == ["alice", "bob"]

    async with client(app, "globex") as c:
        assert [u["username"] for u in (await c.get("/users", headers=AUTH)).json()] == ["carol"]


async def test_users_requires_admin_token(app, store: MongoStore):
    await store.tenant_registry().create("acme")
    async with client(app) as c:
        assert (await c.get("/users")).status_code == 401
        assert (await c.get("/users", headers={"Authorization": "Bearer wrong"})).status_code == 401


async def test_unknown_or_inactive_tenant_gets_404(app, store: MongoStore):
    registry = store.tenant_registry()
    off = await registry.create("off")
    await registry.set_active(off.tenant_id, False)
    for sub in ("nope", "off"):
        async with client(app, sub) as c:
            assert (await c.get("/users", headers=AUTH)).status_code == 404


async def test_rule_crud_roundtrip(app, store: MongoStore):
    await store.tenant_registry().create("acme")
    async with client(app) as c:
        assert (await c.put("/rules/send_message", json=RULE, headers=AUTH)).status_code == 200
        assert (await c.get("/rules", headers=AUTH)).json() == [
            {**RULE, "deny": [], "require_approval": []}
        ]
        assert (await c.delete("/rules/send_message", headers=AUTH)).status_code == 204
        assert (await c.delete("/rules/send_message", headers=AUTH)).status_code == 404


async def test_rule_validation(app, store: MongoStore):
    await store.tenant_registry().create("acme")
    async with client(app) as c:
        bad_regex = {**RULE, "constraints": {"message": {"reject_pattern": "("}}}
        assert (await c.put("/rules/send_message", json=bad_regex, headers=AUTH)).status_code == 422
        mismatch = {**RULE, "tool": "other"}
        assert (await c.put("/rules/send_message", json=mismatch, headers=AUTH)).status_code == 422


async def test_audit_is_read_only(app, store: MongoStore):
    await store.tenant_registry().create("acme")
    async with client(app) as c:
        assert (await c.get("/audit", headers=AUTH)).status_code == 200
        assert (await c.post("/audit", json={}, headers=AUTH)).status_code == 405
        assert (await c.delete("/audit", headers=AUTH)).status_code == 405
