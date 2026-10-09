"""FastAPI admin server: where an admin configures rules, users, approvals; reads audit."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import Depends, FastAPI

from admin.auth import require_admin
from admin.routers import approvals, audit, health, login, revocations, rules, users
from common.config import Settings
from common.store.mongo import MongoStore
from common.store.resolve import TenantMiddleware


def create_app() -> FastAPI:
    """Build the admin app.

    Every request is resolved to a tenant from its Host subdomain (TenantMiddleware) and
    must carry the admin bearer token. Handlers just call the store; the tenant comes from
    the request context.
    """
    settings = Settings.from_env()
    store = MongoStore(settings.mongo_url, settings.mongo_db)
    registry = store.tenant_registry()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await store.init()
        await registry.init()
        try:
            yield
        finally:
            await store.close()

    app = FastAPI(title="policy-gateway admin", lifespan=lifespan)
    app.state.store = store
    guard = [Depends(require_admin)]
    for module in (rules, users, approvals, audit, revocations, health, login):
        app.include_router(module.router, dependencies=guard)
    app.add_middleware(TenantMiddleware, registry=registry, base_domain=settings.base_domain)
    return app


def main() -> None:
    """Run the admin app with uvicorn on ADMIN_PORT (default 8081)."""
    import os

    uvicorn.run(create_app(), host="127.0.0.1", port=int(os.environ.get("ADMIN_PORT", "8081")))


if __name__ == "__main__":
    main()
