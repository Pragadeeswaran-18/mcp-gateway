"""MongoDB implementation of PolicyStore, tenant-scoped through store.orm.

Every method operates on the tenant set with store.tenant.use_tenant(); with none set it
raises TenantError (fail closed).
Collections: rules (key=tool), users (key=username), approvals (key=id), audit_events, revoked_jtis (TTL on expires_at).
"""

from typing import Any

from pymongo import AsyncMongoClient

from admin.models import ApprovalRequest, AuditEvent, RevokedToken, ToolRule, User
from store.orm import Repository, TenantDB
from store.tenant import current_tenant

INDEXES = {
    "approvals": [[("status", 1)]],
    "audit_events": [[("human", 1), ("ts", -1)], [("tool", 1), ("ts", -1)]],
}


class MongoStore:
    """PolicyStore backed by MongoDB."""

    def __init__(self, url: str, db_name: str) -> None:
        """Create the client; it connects lazily."""
        self._client: AsyncMongoClient = AsyncMongoClient(url, serverSelectionTimeoutMS=5000)
        self._tdb = TenantDB(self._client[db_name])

    def _scope(self):
        return self._tdb.scope(current_tenant())

    def _rules(self) -> Repository[ToolRule]:
        return self._scope().repo("rules", ToolRule, "tool")

    def _users(self) -> Repository[User]:
        return self._scope().repo("users", User, "username")

    def _approvals(self) -> Repository[ApprovalRequest]:
        return self._scope().repo("approvals", ApprovalRequest, "id")

    def _audit(self) -> Repository[AuditEvent]:
        return self._scope().repo("audit_events", AuditEvent, None, append_only=True)

    def _revoked(self) -> Repository[RevokedToken]:
        return self._scope().repo("revoked_jtis", RevokedToken, "jti")

    async def init(self) -> None:
        """Create tenant-leading indexes. Making audit_events truly append-only also needs a
        MongoDB role without update/delete on that collection (see README)."""
        await self._tdb.ensure_indexes(INDEXES)
        await self._tdb.ensure_ttl_index("revoked_jtis", "expires_at")

    async def close(self) -> None:
        await self._client.close()

    async def list_rules(self) -> list[ToolRule]:
        return await self._rules().find()

    async def get_rule(self, tool: str) -> ToolRule | None:
        return await self._rules().get(tool)

    async def put_rule(self, rule: ToolRule) -> None:
        await self._rules().put(rule)

    async def delete_rule(self, tool: str) -> bool:
        return await self._rules().delete(tool)

    async def list_users(self) -> list[User]:
        return await self._users().find()

    async def put_user(self, user: User) -> None:
        await self._users().put(user)

    async def delete_user(self, username: str) -> bool:
        return await self._users().delete(username)

    async def create_approval(self, req: ApprovalRequest) -> None:
        await self._approvals().insert(req)

    async def list_approvals(self, status: str | None = None) -> list[ApprovalRequest]:
        return await self._approvals().find({"status": status} if status else None)

    async def resolve_approval(self, approval_id: str, approved: bool, by: str) -> bool:
        return await self._approvals().update_where(
            {"id": approval_id, "status": "pending"},
            {"status": "approved" if approved else "denied", "resolved_by": by},
        )

    async def revoke_token(self, token: RevokedToken) -> None:
        await self._revoked().put(token)

    async def is_revoked(self, jti: str) -> bool:
        return await self._revoked().get(jti) is not None

    async def append_audit(self, event: AuditEvent) -> None:
        await self._audit().insert(event)

    async def query_audit(self, filters: dict[str, Any], limit: int = 100) -> list[AuditEvent]:
        return await self._audit().find(filters, sort=[("ts", -1)], limit=limit)
