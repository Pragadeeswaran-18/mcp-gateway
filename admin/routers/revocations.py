"""Revoke gateway JWTs by jti."""

from fastapi import APIRouter

from admin.models import RevokedToken

router = APIRouter(prefix="/revocations", tags=["revocations"])


@router.post("/{jti}", status_code=201)
async def revoke(jti: str, human: str, expires_at: int) -> RevokedToken:
    """Revoke token `jti` for the request's tenant.

    `expires_at` is the token's exp (unix seconds) so the row can expire with it. Must
    record the admin as revoked_by, write an audit event, and be idempotent.
    """
    raise NotImplementedError


@router.get("/{jti}")
async def is_revoked(jti: str) -> dict[str, bool]:
    """Return {"revoked": bool} for this tenant."""
    raise NotImplementedError
