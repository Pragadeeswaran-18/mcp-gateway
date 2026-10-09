"""Settings read from the environment, shared by the admin server and the gateway."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    mongo_url: str
    mongo_db: str
    base_domain: str
    admin_token: str | None

    @classmethod
    def from_env(cls) -> "Settings":
        """Read settings at call time (not import time) so tests can monkeypatch the env."""
        return cls(
            mongo_url=os.environ.get("MONGO_URL", "mongodb://localhost:27017"),
            mongo_db=os.environ.get("MONGO_DB", "policy_gateway"),
            base_domain=os.environ.get("BASE_DOMAIN", "localhost"),
            admin_token=os.environ.get("ADMIN_TOKEN") or None,
        )
