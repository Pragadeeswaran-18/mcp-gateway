"""Global (not tenant-scoped) registry mapping subdomains to numeric tenant ids."""

from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import DuplicateKeyError

from common.models import Tenant
from common.store.tenant import TenantError


class TenantRegistry:
    """The `tenants` collection: {_id: tenant_id, subdomain, active}.

    This is the one collection that is intentionally not tenant-scoped; only admin
    tooling and the host resolver should touch it.
    """

    def __init__(self, db: AsyncDatabase) -> None:
        self._tenants = db["tenants"]
        self._counters = db["counters"]

    async def init(self) -> None:
        """Unique index on subdomain (tenant_id is the _id, so already unique)."""
        await self._tenants.create_index("subdomain", unique=True)

    async def create(self, subdomain: str) -> Tenant:
        """Allocate the next numeric id and register `subdomain`; TenantError if taken."""
        counter = await self._counters.find_one_and_update(
            {"_id": "tenant_id"}, {"$inc": {"seq": 1}}, upsert=True, return_document=True
        )
        tenant = Tenant(tenant_id=counter["seq"], subdomain=subdomain)
        try:
            await self._tenants.insert_one(
                {"_id": tenant.tenant_id, "subdomain": subdomain, "active": True}
            )
        except DuplicateKeyError as exc:
            raise TenantError(f"subdomain already registered: {subdomain!r}") from exc
        return tenant

    async def get_by_subdomain(self, subdomain: str) -> Tenant | None:
        doc = await self._tenants.find_one({"subdomain": subdomain})
        if doc is None:
            return None
        return Tenant(tenant_id=doc["_id"], subdomain=doc["subdomain"], active=doc["active"])

    async def set_active(self, tenant_id: int, active: bool) -> bool:
        res = await self._tenants.update_one({"_id": tenant_id}, {"$set": {"active": active}})
        return res.matched_count == 1
