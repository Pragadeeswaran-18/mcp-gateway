"""JWT claims (no database) and jti revocation storage (needs MongoDB)."""

from datetime import UTC, datetime, timedelta

import jwt
from mint_jwt import mint

from admin.models import RevokedToken
from store.mongo import MongoStore
from store.tenant import use_tenant

SECRET = "x" * 32


def test_minted_tokens_carry_tenant_and_unique_jti():
    a = jwt.decode(mint("alice", SECRET, tenant_id=7), SECRET, algorithms=["HS256"])
    b = jwt.decode(mint("alice", SECRET), SECRET, algorithms=["HS256"])
    assert a["tenant_id"] == 7 and b["tenant_id"] == 1
    assert a["jti"] != b["jti"] and len(a["jti"]) == 32


def _token(jti: str) -> RevokedToken:
    now = datetime.now(UTC)
    return RevokedToken(
        jti=jti,
        human="alice",
        revoked_by="admin",
        revoked_at=now,
        expires_at=now + timedelta(hours=1),
    )


async def test_revocation_is_per_tenant_and_idempotent(store: MongoStore):
    await store.init()
    with use_tenant(1):
        assert await store.is_revoked("j1") is False
        await store.revoke_token(_token("j1"))
        await store.revoke_token(_token("j1"))
        assert await store.is_revoked("j1") is True
    with use_tenant(2):
        assert await store.is_revoked("j1") is False


async def test_revoked_rows_have_ttl_index(store: MongoStore):
    await store.init()
    info = await store._tdb.db["revoked_jtis"].index_information()
    assert any(
        v.get("expireAfterSeconds") == 0 and v["key"] == [("expires_at", 1)] for v in info.values()
    )
