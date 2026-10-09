"""RSA keys and tokens for the admin API.

  uv run python scripts/admin_keys.py genkeys        # writes keys/admin_{private,public}.pem
  uv run python scripts/admin_keys.py token [sub]    # prints a 1h RS256 admin token

The admin server only needs the PUBLIC key (ADMIN_JWT_PUBLIC_KEY_FILE). Keep the private key
off the server; whoever holds it can mint admin tokens.
"""

import os
import sys
import time
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

KEYS = Path("keys")
AUDIENCE = os.environ.get("ADMIN_JWT_AUDIENCE", "policy-gateway-admin")


def generate_keypair() -> tuple[bytes, bytes]:
    """Return (private_pem, public_pem) for a new 2048-bit RSA key."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return private, public


def mint_admin(
    private_pem: bytes | str, sub: str = "admin", ttl: int = 3600, audience: str = AUDIENCE
) -> str:
    """Return a signed RS256 admin token."""
    claims = {"sub": sub, "role": "admin", "aud": audience, "exp": int(time.time()) + ttl}
    return jwt.encode(claims, private_pem, algorithm="RS256")


def main() -> int:
    cmd, *rest = sys.argv[1:] or [""]
    if cmd == "genkeys":
        private_path, public_path = KEYS / "admin_private.pem", KEYS / "admin_public.pem"
        if private_path.exists() or public_path.exists():
            print(f"refusing to overwrite existing keys in {KEYS}/", file=sys.stderr)
            return 1
        KEYS.mkdir(exist_ok=True)
        private, public = generate_keypair()
        private_path.write_bytes(private)
        public_path.write_bytes(public)
        print(f"wrote {private_path} and {public_path}")
        return 0
    if cmd == "token":
        path = Path(os.environ.get("ADMIN_JWT_PRIVATE_KEY_FILE", KEYS / "admin_private.pem"))
        if not path.is_file():
            print(f"private key not found: {path} (run genkeys)", file=sys.stderr)
            return 1
        print(mint_admin(path.read_bytes(), rest[0] if rest else "admin"))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
