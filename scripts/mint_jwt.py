"""Mint test HS256 JWTs: uv run python scripts/mint_jwt.py alice|bob|admin"""

import os
import sys
import time

import jwt

USERS = ("alice", "bob", "admin")


def mint(user: str, secret: str, ttl: int = 3600) -> str:
    """Return a signed JWT for `user` with sub, agent_id, task_id and exp claims."""
    if user not in USERS:
        raise ValueError(f"unknown user {user!r}; expected one of {USERS}")
    claims = {
        "sub": user,
        "agent_id": f"agent-{user}",
        "task_id": f"task-{user}-1",
        "exp": int(time.time()) + ttl,
    }
    return jwt.encode(claims, secret, algorithm="HS256")


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in USERS:
        print(f"usage: mint_jwt.py {{{'|'.join(USERS)}}}", file=sys.stderr)
        return 2
    secret = os.environ.get("GATEWAY_JWT_SECRET")
    if not secret:
        print("GATEWAY_JWT_SECRET is not set", file=sys.stderr)
        return 1
    print(mint(sys.argv[1], secret))
    return 0


if __name__ == "__main__":
    sys.exit(main())
