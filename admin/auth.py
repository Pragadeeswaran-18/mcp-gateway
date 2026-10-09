"""Authentication for the admin API."""

from fastapi import Request


async def require_admin(request: Request) -> str:
    """FastAPI dependency: return the admin identity or raise HTTPException(401/403).

    Must: validate the Authorization bearer token (static ADMIN_TOKEN for the prototype,
    or an admin-role JWT) using a constant-time comparison. Gateway end-user tokens must
    never be accepted here.
    """
    raise NotImplementedError
