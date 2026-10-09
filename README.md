# policy-gateway

Prototype MCP policy gateway. It sits between an agent and an upstream MCP server, proxies
calls with FastMCP's `create_proxy()`, and enforces policy in FastMCP middleware:
per-tool allow/deny/require_approval, argument constraints, per-user pinned arguments hidden
from the model, and an audit log tied to a human and an agent.

**Status:** scaffold only. `gateway/`, `admin/` and `store/` are stubbed
(`NotImplementedError`); the upstream server, JWT minting script, pydantic models and tests are
real. The tests fail until those are implemented.

## Components

- `gateway/` - the MCP proxy + policy middleware (agents connect here).
- `admin/` - FastAPI admin server where an admin configures rules, users and approvals and
  reads the audit log (`make admin`, port `ADMIN_PORT`, bearer `ADMIN_TOKEN`).
- `store/` - `PolicyStore` interface and a MongoDB implementation (`make mongo` starts it with
  Docker). The admin writes config here; the gateway reads it.

## Setup

```
uv sync
cp .env.example .env     # then edit; export the variables into your shell
```

## Run

```
make upstream    # uv run python -m upstream.server   (port 9000)
make gateway     # uv run python -m gateway.server    (GATEWAY_PORT, default 8080)
```

```
make mongo      # docker compose up -d mongo
make admin      # uv run python -m admin.app         (port 8081)
```

## MongoDB and tenancy

Point `MONGO_URL` at any MongoDB 6+: `make mongo` (needs Docker), a local Community install,
or a free Atlas cluster. `store/orm.py` is a small tenant-scoped mapper: every document carries
`tenant_id` and an `_id` of `<tenant>:<key>`, every query is wrapped with the tenant clause,
and callers cannot mention `tenant_id`/`_id` in filters. The active tenant comes from
`store.tenant.use_tenant()`; with none set, storage raises `TenantError`.

Tenant ids are positive integers. Each request's tenant is resolved from the Host subdomain
(`acme.<BASE_DOMAIN>` -> `tenants` collection -> numeric id) by `store.resolve.TenantMiddleware`,
a pure ASGI middleware to wrap the admin app and the gateway's HTTP app; unknown or inactive
subdomains get 404. Register tenants with `TenantRegistry.create("acme")`.

## Mint a token

```
export GATEWAY_JWT_SECRET=...
uv run python scripts/mint_jwt.py alice     # or bob, admin
```

## Test

```
uv run pytest
```

`tests/test_admin.py` needs MongoDB running (`make mongo`); it uses a throwaway database.

The test fixtures start the upstream in-process and the gateway as a subprocess with a
temporary audit DB (`GATEWAY_AUDIT_DB`). The audit table contract is documented in
`gateway/audit.py`.

## Things to verify first

- JWT claims are not documented for FastMCP middleware; spike `on_initialize` + `set_state`
  versus decoding the Authorization header in each hook.
- Per-user `inputSchema` editing in `on_list_tools` (docs only show tag filtering).
- The proxy tool-list cache (`cache_ttl`) must not cache per-user output.
- Hidden tools must also be denied in `on_call_tool`.
- How the gateway picks up admin changes (poll, change streams, or per-request read) and what
  it does when MongoDB is down (fail closed).
- The scenario tests still read the audit log from SQLite (`gateway/audit.py`); decide whether
  audit moves fully to MongoDB and update `tests/conftest.py` accordingly.
