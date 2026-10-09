"""FastAPI admin server: where an admin configures rules, users, approvals; reads audit."""

from fastapi import FastAPI

from store.base import PolicyStore


def create_app(store: PolicyStore | None = None) -> FastAPI:
    """Build the admin app.

    Must: default `store` to MongoStore(MONGO_URL, MONGO_DB), call store.init() on startup
    and store.close() on shutdown (lifespan), expose it to routers, and include the
    rules, users, approvals and audit routers, each guarded by auth.require_admin.
    """
    raise NotImplementedError


def main() -> None:
    """Run the admin app with uvicorn on ADMIN_PORT (default 8081)."""
    raise NotImplementedError


if __name__ == "__main__":
    main()
