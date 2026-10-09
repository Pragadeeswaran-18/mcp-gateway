"""MongoDB implementation of PolicyStore (pymongo AsyncMongoClient)."""

from typing import Any

from admin.models import ApprovalRequest, AuditEvent, ToolRule, User


class MongoStore:
    """PolicyStore backed by MongoDB.

    Collections: rules (_id = tool), users (_id = username), approvals, audit_events.
    """

    def __init__(self, url: str, db_name: str) -> None:
        """Create the client from MONGO_URL / MONGO_DB values; do not connect yet.

        Must: use pymongo.AsyncMongoClient and keep the database handle on self.
        """
        raise NotImplementedError

    async def init(self) -> None:
        """Create indexes. Must also make audit_events append-only as far as MongoDB allows
        (e.g. a dedicated DB user without update/delete privileges; document the setup)."""
        raise NotImplementedError

    async def close(self) -> None:
        """Close the client."""
        raise NotImplementedError

    async def list_rules(self) -> list[ToolRule]:
        """See PolicyStore."""
        raise NotImplementedError

    async def get_rule(self, tool: str) -> ToolRule | None:
        """See PolicyStore."""
        raise NotImplementedError

    async def put_rule(self, rule: ToolRule) -> None:
        """See PolicyStore."""
        raise NotImplementedError

    async def delete_rule(self, tool: str) -> bool:
        """See PolicyStore."""
        raise NotImplementedError

    async def list_users(self) -> list[User]:
        """See PolicyStore."""
        raise NotImplementedError

    async def put_user(self, user: User) -> None:
        """See PolicyStore."""
        raise NotImplementedError

    async def delete_user(self, username: str) -> bool:
        """See PolicyStore."""
        raise NotImplementedError

    async def create_approval(self, req: ApprovalRequest) -> None:
        """See PolicyStore."""
        raise NotImplementedError

    async def list_approvals(self, status: str | None = None) -> list[ApprovalRequest]:
        """See PolicyStore."""
        raise NotImplementedError

    async def resolve_approval(self, approval_id: str, approved: bool, by: str) -> bool:
        """See PolicyStore."""
        raise NotImplementedError

    async def append_audit(self, event: AuditEvent) -> None:
        """See PolicyStore."""
        raise NotImplementedError

    async def query_audit(self, filters: dict[str, Any], limit: int = 100) -> list[AuditEvent]:
        """See PolicyStore."""
        raise NotImplementedError
