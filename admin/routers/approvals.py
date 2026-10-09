"""Review of require_approval calls."""

from fastapi import APIRouter

from common.models import ApprovalRequest

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("")
async def list_approvals(status: str | None = None) -> list[ApprovalRequest]:
    """List approval requests, optionally filtered by status."""
    raise NotImplementedError


@router.post("/{approval_id}/approve")
async def approve(approval_id: str) -> ApprovalRequest:
    """Approve a pending request, recording the admin; 409 if not pending."""
    raise NotImplementedError


@router.post("/{approval_id}/deny")
async def deny(approval_id: str) -> ApprovalRequest:
    """Deny a pending request, recording the admin; 409 if not pending."""
    raise NotImplementedError
