"""Tenant identity for the current request/task, carried in a ContextVar.

The admin auth dependency and the gateway's on_initialize hook are expected to call
`use_tenant()` once the caller is authenticated. Storage fails closed when it is unset.
"""

import re
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

_TENANT_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")

_current: ContextVar[str | None] = ContextVar("tenant_id", default=None)


class TenantError(Exception):
    """Raised for any attempt to cross, omit or spoof a tenant boundary."""


def validate_tenant_id(tenant_id: str) -> str:
    """Return `tenant_id` if it is a safe slug, else raise TenantError.

    The pattern excludes ":" (used to namespace document ids) and anything that looks like
    a Mongo operator.
    """
    if not isinstance(tenant_id, str) or not _TENANT_RE.fullmatch(tenant_id):
        raise TenantError(f"invalid tenant id: {tenant_id!r}")
    return tenant_id


def current_tenant() -> str:
    """Return the active tenant id, or raise TenantError if none has been set."""
    tenant_id = _current.get()
    if tenant_id is None:
        raise TenantError("no tenant set for this context")
    return tenant_id


@contextmanager
def use_tenant(tenant_id: str) -> Iterator[str]:
    """Run a block with `tenant_id` as the active tenant."""
    token = _current.set(validate_tenant_id(tenant_id))
    try:
        yield tenant_id
    finally:
        _current.reset(token)
