"""Small upstream MCP server used for testing the gateway."""

from typing import Any

from fastmcp import FastMCP

mcp = FastMCP("upstream")

# Every tool call appends (tool_name, arguments) here so tests can inspect what arrived.
received: list[tuple[str, dict[str, Any]]] = []


@mcp.tool
def read_orders(customer_id: str) -> list[dict[str, Any]]:
    """Return a fake order list for a customer."""
    received.append(("read_orders", {"customer_id": customer_id}))
    return [
        {"order_id": "A-1001", "customer_id": customer_id, "total": 42.5},
        {"order_id": "A-1002", "customer_id": customer_id, "total": 17.0},
    ]


@mcp.tool
def send_message(phone_number: str, message: str) -> str:
    """Send a message to a phone number."""
    received.append(("send_message", {"phone_number": phone_number, "message": message}))
    return "sent"


@mcp.tool
def delete_record(record_id: str) -> str:
    """Delete a record."""
    received.append(("delete_record", {"record_id": record_id}))
    return "deleted"


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=9000)
