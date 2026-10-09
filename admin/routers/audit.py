"""Read-only access to the audit log. No write or delete routes may exist."""

from fastapi import APIRouter

from common.models import AuditEvent

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
async def query_audit(
    human: str | None = None, agent: str | None = None, tool: str | None = None, limit: int = 100
) -> list[AuditEvent]:
    """Return audit events matching the filters, newest first."""
    raise NotImplementedError
