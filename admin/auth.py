"""Authentication for the admin API."""

import hmac

from fastapi import HTTPException, Request

from common.config import Settings


async def require_admin(request: Request) -> str:
    """FastAPI dependency: return the admin identity or raise HTTPException.

    Prototype scheme: a static bearer token (ADMIN_TOKEN), compared in constant time.
    Fails closed with 503 when ADMIN_TOKEN is not configured. Gateway end-user JWTs are
    never accepted here.
    """
    expected = Settings.from_env().admin_token
    if expected is None:
        raise HTTPException(status_code=503, detail="admin auth is not configured")
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not hmac.compare_digest(token.encode(), expected.encode()):
        raise HTTPException(
            status_code=401, detail="invalid admin token", headers={"WWW-Authenticate": "Bearer"}
        )
    return "admin"
