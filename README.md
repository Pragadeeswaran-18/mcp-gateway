# policy-gateway

Prototype MCP policy gateway. It sits between an agent and an upstream MCP server, proxies
calls with FastMCP's `create_proxy()`, and enforces policy in FastMCP middleware:
per-tool allow/deny/require_approval, argument constraints, per-user pinned arguments hidden
from the model, and an audit log tied to a human and an agent.

**Status:** scaffold only. `gateway/` is stubbed (`NotImplementedError`); the upstream server,
JWT minting script and tests are real. The tests fail until the gateway is implemented.

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

## Mint a token

```
export GATEWAY_JWT_SECRET=...
uv run python scripts/mint_jwt.py alice     # or bob, admin
```

## Test

```
uv run pytest
```

The test fixtures start the upstream in-process and the gateway as a subprocess with a
temporary audit DB (`GATEWAY_AUDIT_DB`). The audit table contract is documented in
`gateway/audit.py`.

## Things to verify first

- JWT claims are not documented for FastMCP middleware; spike `on_initialize` + `set_state`
  versus decoding the Authorization header in each hook.
- Per-user `inputSchema` editing in `on_list_tools` (docs only show tag filtering).
- The proxy tool-list cache (`cache_ttl`) must not cache per-user output.
- Hidden tools must also be denied in `on_call_tool`.
