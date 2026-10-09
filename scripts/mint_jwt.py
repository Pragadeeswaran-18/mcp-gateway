"""Mint test HS256 JWTs: uv run python scripts/mint_jwt.py alice|bob|admin"""

import os
import sys
import time
import uuid

import jwt

USERS = ("alice", "bob", "admin")


def mint(user: str, secret: str, ttl: int = 3600, tenant_id: int = 1) -> str:
    """Return a signed JWT for `user` with sub, agent_id, task_id, tenant_id, jti and exp."""
    if user not in USERS:
        raise ValueError(f"unknown user {user!r}; expected one of {USERS}")
    claims = {
        "sub": user,
        "agent_id": f"agent-{user}",
        "task_id": f"task-{user}-1",
        "tenant_id": tenant_id,
        "jti": uuid.uuid4().hex,
        "exp": int(time.time()) + ttl,
    }
    return jwt.encode(claims, secret, algorithm="HS256")


def main() -> int:
    args = sys.argv[1:]
    if (
        len(args) not in (1, 2)
        or args[0] not in USERS
        or (len(args) == 2 and not args[1].isdigit())
    ):
        print(f"usage: mint_jwt.py {{{'|'.join(USERS)}}} [tenant_id]", file=sys.stderr)
        return 2
    secret = os.environ.get("GATEWAY_JWT_SECRET")
    if not secret:
        print("GATEWAY_JWT_SECRET is not set", file=sys.stderr)
        return 1
    print(mint(args[0], secret, tenant_id=int(args[1]) if len(args) == 2 else 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
