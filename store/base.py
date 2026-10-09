"""Storage interface shared by the gateway (reads) and the admin server (reads/writes)."""

from typing import Any, Protocol

from admin.models import ApprovalRequest, AuditEvent, ToolRule, User


class PolicyStore(Protocol):
    """Async persistence for rules, users, approvals and the audit log."""

    async def init(self) -> None:
        """Create collections and indexes (unique tool name / username, audit by human+ts)."""
        ...

    async def close(self) -> None:
        """Release the database connection."""
        ...

    async def list_rules(self) -> list[ToolRule]:
        """Return every tool rule."""
        ...

    async def get_rule(self, tool: str) -> ToolRule | None:
        """Return the rule for `tool`, or None."""
        ...

    async def put_rule(self, rule: ToolRule) -> None:
        """Insert or replace the rule keyed by `rule.tool`."""
        ...

    async def delete_rule(self, tool: str) -> bool:
        """Delete the rule; return whether it existed."""
        ...

    async def list_users(self) -> list[User]:
        """Return every user."""
        ...

    async def put_user(self, user: User) -> None:
        """Insert or replace the user keyed by `user.username`."""
        ...

    async def delete_user(self, username: str) -> bool:
        """Delete the user; return whether it existed."""
        ...

    async def create_approval(self, req: ApprovalRequest) -> None:
        """Persist a pending approval request created by the gateway."""
        ...

    async def list_approvals(self, status: str | None = None) -> list[ApprovalRequest]:
        """List approval requests, optionally filtered by status."""
        ...

    async def resolve_approval(self, approval_id: str, approved: bool, by: str) -> bool:
        """Atomically move a pending request to approved/denied; False if not pending."""
        ...

    async def append_audit(self, event: AuditEvent) -> None:
        """Append one audit event. There is deliberately no update or delete."""
        ...

    async def query_audit(self, filters: dict[str, Any], limit: int = 100) -> list[AuditEvent]:
        """Return audit events matching `filters`, newest first."""
        ...
