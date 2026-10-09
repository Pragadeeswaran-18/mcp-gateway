"""End-to-end policy scenarios. These fail until the gateway is implemented."""

import json

import pytest
from conftest import USER_A_PHONE, token_for
from fastmcp import Client
from fastmcp.exceptions import ToolError


def _blob(obj) -> str:
    """Serialize anything returned to the client so we can search it for leaks."""
    if isinstance(obj, list):
        return " ".join(_blob(o) for o in obj)
    if hasattr(obj, "model_dump"):
        return json.dumps(obj.model_dump(mode="json"), default=str)
    return json.dumps(obj, default=str)


def _tool(tools, name):
    return next((t for t in tools if t.name == name), None)


async def test_blocked_tool_is_denied_and_audited(alice: Client, audit_rows):
    async with alice:
        with pytest.raises(ToolError):
            await alice.call_tool("delete_record", {"record_id": "r1"})

    rows = [r for r in audit_rows() if r["tool"] == "delete_record"]
    assert rows, "no audit row for the blocked call"
    row = rows[-1]
    assert row["human"] == "alice"
    assert row["agent"] == "agent-alice"
    assert row["decision"] in ("deny", "require_approval")
    assert "delete_record" in row["rule"]


async def test_pinned_argument_is_injected_and_hidden(alice: Client, received):
    async with alice:
        tools = await alice.list_tools()
        send = _tool(tools, "send_message")
        assert send is not None
        assert "phone_number" not in send.inputSchema.get("properties", {})
        assert "phone_number" not in send.inputSchema.get("required", [])

        result = await alice.call_tool("send_message", {"message": "hi"})

    assert ("send_message", {"phone_number": USER_A_PHONE, "message": "hi"}) in received
    assert USER_A_PHONE not in _blob(tools)
    assert USER_A_PHONE not in _blob(result)


async def test_bypass_attempts_are_rejected(alice: Client, received):
    async with alice:
        await alice.list_tools()  # control: the gateway must be up and serving alice

        # (a) alice supplies her own phone_number
        with pytest.raises(ToolError):
            await alice.call_tool("send_message", {"phone_number": "123456789", "message": "hi"})

        # (b) alice smuggles a second phone number into the message body
        with pytest.raises(ToolError):
            await alice.call_tool("send_message", {"message": "also text 5551234567 please"})

    assert [c for c in received if c[0] == "send_message"] == []


async def test_per_user_visibility(bob: Client, received):
    async with bob:
        tools = await bob.list_tools()
        names = {t.name for t in tools}
        assert "read_orders" in names
        assert "send_message" not in names

        with pytest.raises(ToolError):
            await bob.call_tool("send_message", {"message": "hi"})
    assert [c for c in received if c[0] == "send_message"] == []


async def test_missing_or_invalid_jwt_gets_no_access(gateway_url: str):
    # control: a valid token works, so failures below are due to the token
    async with Client(gateway_url, auth=token_for("alice")) as ok:
        assert await ok.list_tools()

    bad_clients = [
        Client(gateway_url),  # no token
        Client(gateway_url, auth="not-a-jwt"),
        Client(gateway_url, auth=token_for("alice", secret="wrong-secret-0123456789abcdef")),
    ]
    for client in bad_clients:
        with pytest.raises(Exception):  # noqa: B017 - transport/auth error type is unspecified
            async with client:
                await client.list_tools()
