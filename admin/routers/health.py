"""Liveness probe; exempt from admin auth (but still needs a resolvable tenant host)."""

from fastapi import APIRouter

from admin.auth import public

router = APIRouter(tags=["health"])


@router.get("/healthz")
@public
async def healthz() -> dict[str, str]:
    """Return {"status": "ok"}."""
    return {"status": "ok"}
