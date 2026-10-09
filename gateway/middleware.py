"""FastMCP middleware enforcing policy between the agent and the upstream server."""

from typing import Any

from fastmcp.server.middleware import Middleware, MiddlewareContext


class PolicyMiddleware(Middleware):
    """Enforces policy on initialize, tools/list and tools/call."""

    async def on_initialize(self, context: MiddlewareContext[Any], call_next: Any) -> Any:
        """Authenticate the caller and build a Session.

        Must: validate the JWT (HS256, GATEWAY_JWT_SECRET, exp), extract sub/agent_id/task_id,
        store the Session where later hooks can read it, check the token's tenant_id matches
        the subdomain tenant and that its jti is not revoked (PolicyStore.is_revoked, fail
        closed if the store is unreachable), and reject the handshake when the token is
        missing or invalid.
        """
        raise NotImplementedError

    async def on_list_tools(self, context: MiddlewareContext[Any], call_next: Any) -> Any:
        """Return only the tools this session may see, with pinned parameters removed.

        Must: drop tools denied to the user, strip pinned arguments from each inputSchema
        (properties and required), and never leak pinned values.
        """
        raise NotImplementedError

    async def on_call_tool(self, context: MiddlewareContext[Any], call_next: Any) -> Any:
        """Evaluate policy for the call, audit it, and forward or refuse.

        Must: re-check jti revocation, deny hidden/denied tools, refuse require_approval calls, reject conflicting
        or constraint-violating arguments, inject pinned values, write an audit event for
        every outcome, and ensure rejected calls never reach the upstream.
        """
        raise NotImplementedError
