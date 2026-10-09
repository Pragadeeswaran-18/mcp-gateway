"""A small tenant-scoped document mapper on top of pymongo's async API.

Isolation rules, all enforced here so callers cannot forget them:
  * every document stores `tenant_id` and has `_id == "<tenant_id>:<key>"`, so the same key
    can exist in two tenants and one tenant can never overwrite another's document;
  * every read/update/delete filter is wrapped as {"$and": [{"tenant_id": t}, filter]};
  * callers may not mention `tenant_id` or `_id` in filters or updates, nor use server-side
    JavaScript operators;
  * models never carry `tenant_id`; it is stamped on write and stripped on read.
"""

import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase

from common.store.tenant import TenantError, validate_tenant_id

_RESERVED = {"tenant_id", "_id"}
_FORBIDDEN_OPERATORS = {"$where", "$function", "$accumulator"}


class AppendOnlyError(Exception):
    """Raised when a mutation is attempted on an append-only collection."""


def check_filter(obj: Any) -> None:
    """Reject filters/updates that name reserved fields or run server-side JavaScript."""
    if isinstance(obj, Mapping):
        for key, value in obj.items():
            if key in _RESERVED or key in _FORBIDDEN_OPERATORS:
                raise TenantError(f"field not allowed in tenant-scoped query: {key!r}")
            check_filter(value)
    elif isinstance(obj, Sequence) and not isinstance(obj, str | bytes):
        for item in obj:
            check_filter(item)


def scope_filter(tenant_id: int, flt: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return `flt` confined to `tenant_id`."""
    check_filter(flt or {})
    if not flt:
        return {"tenant_id": tenant_id}
    return {"$and": [{"tenant_id": tenant_id}, dict(flt)]}


def doc_id(tenant_id: int, key: str) -> str:
    """Namespaced primary key."""
    return f"{tenant_id}:{key}"


def to_doc(tenant_id: int, key: str, item: BaseModel) -> dict[str, Any]:
    """Serialise a model into a stored document."""
    data = item.model_dump()
    if _RESERVED & data.keys():
        raise TenantError("model must not define tenant_id or _id fields")
    return {"_id": doc_id(tenant_id, key), "tenant_id": tenant_id, **data}


def from_doc[M: BaseModel](model: type[M], doc: Mapping[str, Any]) -> M:
    """Rebuild a model from a stored document, dropping storage-only fields."""
    return model.model_validate({k: v for k, v in doc.items() if k not in _RESERVED})


class Repository[M: BaseModel]:
    """CRUD for one collection and one model, confined to a single tenant."""

    def __init__(
        self,
        collection: AsyncCollection,
        model: type[M],
        tenant_id: int,
        key_field: str | None,
    ) -> None:
        """`key_field` names the model attribute used as the key; None means generated ids."""
        self._col = collection
        self._model = model
        self._tenant = validate_tenant_id(tenant_id)
        self._key_field = key_field

    def _key(self, item: M) -> str:
        if self._key_field is None:
            return uuid.uuid4().hex
        return str(getattr(item, self._key_field))

    async def get(self, key: str) -> M | None:
        doc = await self._col.find_one(
            {"_id": doc_id(self._tenant, key), "tenant_id": self._tenant}
        )
        return from_doc(self._model, doc) if doc else None

    async def filter(
        self,
        flt: Mapping[str, Any] | None = None,
        *,
        sort: list[tuple[str, int]] | None = None,
        limit: int = 0,
    ) -> list[M]:
        cursor = self._col.find(scope_filter(self._tenant, flt))
        if sort:
            cursor = cursor.sort(sort)
        if limit:
            cursor = cursor.limit(limit)
        return [from_doc(self._model, d) async for d in cursor]

    async def insert(self, item: M) -> None:
        """Insert a new document; raises on duplicate key."""
        await self._col.insert_one(to_doc(self._tenant, self._key(item), item))

    async def put(self, item: M) -> None:
        """Insert or replace the document with this item's key."""
        if self._key_field is None:
            raise TenantError("put() needs a keyed repository; use insert()")
        doc = to_doc(self._tenant, self._key(item), item)
        await self._col.replace_one(
            {"_id": doc["_id"], "tenant_id": self._tenant}, doc, upsert=True
        )

    async def delete(self, key: str) -> bool:
        res = await self._col.delete_one(
            {"_id": doc_id(self._tenant, key), "tenant_id": self._tenant}
        )
        return res.deleted_count == 1

    async def edit(self, flt: Mapping[str, Any], changes: Mapping[str, Any]) -> bool:
        """Atomically $set `changes` on one matching document; return whether one matched."""
        check_filter(changes)
        res = await self._col.update_one(scope_filter(self._tenant, flt), {"$set": dict(changes)})
        return res.modified_count == 1


class AppendOnlyRepository[M: BaseModel](Repository[M]):
    """Repository that only supports get/list/insert."""

    async def put(self, item: M) -> None:
        raise AppendOnlyError("collection is append-only")

    async def delete(self, key: str) -> bool:
        raise AppendOnlyError("collection is append-only")

    async def edit(self, flt: Mapping[str, Any], changes: Mapping[str, Any]) -> bool:
        raise AppendOnlyError("collection is append-only")


class TenantScope:
    """A database handle bound to one tenant; hands out repositories."""

    def __init__(self, db: AsyncDatabase, tenant_id: int) -> None:
        self._db = db
        self.tenant_id = validate_tenant_id(tenant_id)

    def repo[M: BaseModel](
        self,
        name: str,
        model: type[M],
        key_field: str | None = None,
        *,
        append_only: bool = False,
    ) -> Repository[M]:
        cls = AppendOnlyRepository if append_only else Repository
        return cls(self._db[name], model, self.tenant_id, key_field)


class TenantDB:
    """Entry point: `TenantDB(db).scope("acme").repo(...)`."""

    def __init__(self, db: AsyncDatabase) -> None:
        self.db = db

    def scope(self, tenant_id: int) -> TenantScope:
        return TenantScope(self.db, tenant_id)

    async def ensure_ttl_index(self, collection: str, field: str) -> None:
        """Delete documents once `field` (a date) has passed. TTL indexes must be
        single-field, so this one does not lead with tenant_id; it only expires rows."""
        await self.db[collection].create_index(field, expireAfterSeconds=0)

    async def ensure_indexes(
        self, indexes: Mapping[str, Sequence[Sequence[tuple[str, int]]]]
    ) -> None:
        """Create indexes, always leading with tenant_id so queries stay tenant-local."""
        for name, specs in indexes.items():
            for spec in specs:
                await self.db[name].create_index([("tenant_id", 1), *spec])
