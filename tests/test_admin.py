"""Admin API scenarios (need MongoDB). Unbuilt endpoints fail with NotImplementedError."""

import base64
import hashlib
import hmac
import json
import time

import httpx
import jwt
import pytest
from admin_keys import generate_keypair, mint_admin
from conftest import MONGO_URL
from httpx import ASGITransport

from admin.app import create_app
from common.models import User
from common.store.mongo import MongoStore
from common.store.tenant import use_tenant

PRIVATE_PEM, PUBLIC_PEM = generate_keypair()
OTHER_PRIVATE_PEM, _ = generate_keypair()


def _hs256_with_public_key(claims: dict) -> str:
    def b64(raw: bytes) -> bytes:
        return base64.urlsafe_b64encode(raw).rstrip(b"=")

    head = b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = b64(json.dumps(claims).encode())
    sig = hmac.new(PUBLIC_PEM, head + b"." + body, hashlib.sha256).digest()
    return (head + b"." + body + b"." + b64(sig)).decode()


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


AUTH = bearer(mint_admin(PRIVATE_PEM))

RULE = {
    "tool": "send_message",
    "allow": ["alice"],
    "pins": {"phone_number": {"value": "ref:USER_A_PHONE", "on_conflict": "reject"}},
    "constraints": {"message": {"reject_pattern": r"\d{9,}"}},
}


@pytest.fixture
async def app(store: MongoStore, monkeypatch: pytest.MonkeyPatch):
    """Admin app on a throwaway database with its lifespan running."""
    monkeypatch.setenv("ADMIN_JWT_PUBLIC_KEY", PUBLIC_PEM.decode())
    monkeypatch.setenv("ADMIN_JWT_AUDIENCE", "policy-gateway-admin")
    monkeypatch.setenv("BASE_DOMAIN", "localhost")
    # create_app() builds its own store from the environment; point it at the test database
    monkeypatch.setenv("MONGO_URL", MONGO_URL)
    monkeypatch.setenv("MONGO_DB", store._tdb.db.name)
    app = create_app()
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


async def _status(app, headers=None) -> int:
    async with client(app) as c:
        return (await c.get("/users", headers=headers)).status_code


async def test_admin_token_validation(app, store: MongoStore):
    await store.tenant_registry().create("acme")
    now = int(time.time())
    claims = {"sub": "admin", "role": "admin", "aud": "policy-gateway-admin", "exp": now + 600}

    def rs256(key, **override):
        return bearer(jwt.encode({**claims, **override}, key, algorithm="RS256"))

    assert await _status(app, AUTH) == 200
    assert await _status(app) == 401  # no token
    assert await _status(app, bearer("garbage")) == 401
    assert await _status(app, rs256(OTHER_PRIVATE_PEM)) == 401  # signed by another key
    assert await _status(app, rs256(PRIVATE_PEM, exp=now - 10)) == 401  # expired
    assert await _status(app, rs256(PRIVATE_PEM, aud="someone-else")) == 401
    assert await _status(app, rs256(PRIVATE_PEM, role="user")) == 403  # not an admin
    # algorithm confusion: HS256 token "signed" with the public key must not verify
    # (PyJWT refuses to build one, so assemble it by hand as an attacker would.)
    assert await _status(app, bearer(_hs256_with_public_key(claims))) == 401


async def test_admin_fails_closed_without_a_public_key(app, store: MongoStore, monkeypatch):
    await store.tenant_registry().create("acme")
    monkeypatch.delenv("ADMIN_JWT_PUBLIC_KEY")
    monkeypatch.delenv("ADMIN_JWT_PUBLIC_KEY_FILE", raising=False)
    assert await _status(app, AUTH) == 503


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


async def test_public_decorator_exempts_only_marked_routes(app, store: MongoStore):
    await store.tenant_registry().create("acme")
    async with client(app) as c:
        res = await c.get("/healthz")  # no token, marked @public
        assert (res.status_code, res.json()) == (200, {"status": "ok"})
        assert (await c.get("/users")).status_code == 401  # same app, unmarked route
        assert (await c.get("/rules")).status_code == 401
    async with client(app, "nope") as c:
        assert (await c.get("/healthz")).status_code == 404  # tenant is still required
