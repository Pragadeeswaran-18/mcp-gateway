"""Settings read from the environment, shared by the admin server and the gateway."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    mongo_url: str
    mongo_db: str
    base_domain: str
    admin_public_key: str | None  # PEM; verifies RS256 admin tokens
    admin_audience: str

    @classmethod
    def from_env(cls) -> "Settings":
        """Read settings at call time (not import time) so tests can monkeypatch the env."""
        return cls(
            mongo_url=os.environ.get("MONGO_URL", "mongodb://localhost:27017"),
            mongo_db=os.environ.get("MONGO_DB", "policy_gateway"),
            base_domain=os.environ.get("BASE_DOMAIN", "localhost"),
            admin_public_key=_admin_public_key(),
            admin_audience=os.environ.get("ADMIN_JWT_AUDIENCE", "policy-gateway-admin"),
        )


def _admin_public_key() -> str | None:
    """PEM from ADMIN_JWT_PUBLIC_KEY, else from the file named by ADMIN_JWT_PUBLIC_KEY_FILE."""
    pem = os.environ.get("ADMIN_JWT_PUBLIC_KEY")
    if pem:
        return pem
    path = os.environ.get("ADMIN_JWT_PUBLIC_KEY_FILE")
    if path and Path(path).is_file():
        return Path(path).read_text()
    return None
