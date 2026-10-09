"""Resolve the tenant for each HTTP request from the Host header's subdomain.

`acme.gateway.example.com` with base domain `gateway.example.com` -> subdomain `acme` ->
numeric tenant id from the registry. Unknown, inactive or malformed hosts get 404 and no
tenant is ever set.
"""

import os
import re
from typing import Protocol

from common.models import Tenant
from common.store.tenant import use_tenant

_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


class _Registry(Protocol):
    async def get_by_subdomain(self, subdomain: str) -> Tenant | None: ...


def subdomain_from_host(host: str, base_domain: str) -> str | None:
    """Return the single subdomain label of `host` under `base_domain`, else None.

    The port is ignored, matching is case-insensitive, and `host` must be exactly
    `<label>.<base_domain>`: no bare base domain, no nested subdomains.
    """
    host = host.split(":", 1)[0].strip().lower().rstrip(".")
    suffix = "." + base_domain.lower()
    if not host.endswith(suffix):
        return None
    label = host[: -len(suffix)]
    return label if _LABEL_RE.fullmatch(label) else None


class TenantMiddleware:
    """Pure ASGI middleware (works for FastAPI and FastMCP's http_app).

    Sets the tenant context for the duration of each HTTP request. It is not
    BaseHTTPMiddleware on purpose: that runs handlers in a separate task and would lose
    the ContextVar.
    """

    def __init__(self, app, registry: _Registry, base_domain: str | None = None) -> None:
        self.app = app
        self.registry = registry
        self.base_domain = base_domain or os.environ.get("BASE_DOMAIN", "localhost")

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope["headers"])
        host = headers.get(b"host", b"").decode("latin-1")
        subdomain = subdomain_from_host(host, self.base_domain)
        tenant = await self.registry.get_by_subdomain(subdomain) if subdomain else None
        if tenant is None or not tenant.active:
            await send(
                {
                    "type": "http.response.start",
                    "status": 404,
                    "headers": [(b"content-type", b"application/json")],
                }
            )
            await send({"type": "http.response.body", "body": b'{"detail":"unknown tenant"}'})
            return
        with use_tenant(tenant.tenant_id):
            await self.app(scope, receive, send)
