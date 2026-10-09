"""Login endpoint. Public: callers have no admin token yet."""

from fastapi import APIRouter

from admin.auth import public

router = APIRouter(tags=["login"])


@router.post("/login")
@public
async def login() -> dict[str, str]:
    """Authenticate with credentials and return a token.

    Must: verify credentials without revealing which part was wrong, rate limit attempts,
    audit the outcome, and never return more than a short-lived token.
    """
    raise NotImplementedError
