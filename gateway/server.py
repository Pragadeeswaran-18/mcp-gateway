"""Gateway entry point: proxy the upstream MCP server and enforce policy."""

from fastmcp import FastMCP


def build_gateway() -> FastMCP:
    """Build the gateway server.

    Must: create a proxy to UPSTREAM_URL with fastmcp.server.create_proxy(), add
    PolicyMiddleware, initialise the audit DB, and make sure the proxy's tool-list cache
    never serves one user's filtered output to another.
    """
    raise NotImplementedError


def main() -> None:
    """Build the gateway and run it with transport="http" on GATEWAY_PORT."""
    raise NotImplementedError


if __name__ == "__main__":
    main()
