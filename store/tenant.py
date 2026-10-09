"""Tenant identity for the current request/task, carried in a ContextVar.

Tenant ids are positive integers. They are resolved from the request's subdomain by
store.resolve.TenantMiddleware, which calls `use_tenant()`. Storage fails closed when no
tenant is set.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

_current: ContextVar[int | None] = ContextVar("tenant_id", default=None)


class TenantError(Exception):
    """Raised for any attempt to cross, omit or spoof a tenant boundary."""


def validate_tenant_id(tenant_id: int) -> int:
    """Return `tenant_id` if it is a positive int (bool excluded), else raise TenantError."""
    if isinstance(tenant_id, bool) or not isinstance(tenant_id, int) or tenant_id < 1:
        raise TenantError(f"invalid tenant id: {tenant_id!r}")
    return tenant_id


def current_tenant() -> int:
    """Return the active tenant id, or raise TenantError if none has been set."""
    tenant_id = _current.get()
    if tenant_id is None:
        raise TenantError("no tenant set for this context")
    return tenant_id


@contextmanager
def use_tenant(tenant_id: int) -> Iterator[int]:
    """Run a block with `tenant_id` as the active tenant."""
    token = _current.set(validate_tenant_id(tenant_id))
    try:
        yield tenant_id
    finally:
        _current.reset(token)
