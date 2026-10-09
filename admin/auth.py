"""Authentication for the admin API: RS256 JWTs verified with a public key."""

import jwt
from fastapi import HTTPException, Request

from common.config import Settings


def _unauthorized(detail: str = "invalid admin token") -> HTTPException:
    return HTTPException(401, detail, headers={"WWW-Authenticate": "Bearer"})


async def require_admin(request: Request) -> str:
    """FastAPI dependency: return the admin's `sub` or raise HTTPException.

    The bearer token must be an RS256 JWT signed by the admin private key, with `exp`,
    `sub`, `aud` equal to ADMIN_JWT_AUDIENCE and `role == "admin"`. Only RS256 is accepted,
    which blocks algorithm-confusion attacks (an HS256 token "signed" with the public key).
    Gateway end-user tokens carry no admin audience/role and are rejected. Fails closed
    with 503 when no public key is configured or it cannot be parsed.
    """
    settings = Settings.from_env()
    if settings.admin_public_key is None:
        raise HTTPException(503, "admin auth is not configured")
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise _unauthorized("missing bearer token")
    try:
        claims = jwt.decode(
            token,
            settings.admin_public_key,
            algorithms=["RS256"],
            audience=settings.admin_audience,
            options={"require": ["exp", "sub", "aud"]},
        )
    except (jwt.InvalidKeyError, ValueError) as exc:
        raise HTTPException(503, "admin auth is misconfigured") from exc
    except jwt.PyJWTError as exc:
        raise _unauthorized() from exc
    if claims.get("role") != "admin":
        raise HTTPException(403, "admin role required")
    return str(claims["sub"])
