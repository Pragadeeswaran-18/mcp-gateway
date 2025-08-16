import asyncio
import logging
import typing as t
import os
from dotenv import load_dotenv

from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import Response, JSONResponse
from starlette.requests import Request
import uvicorn

from mcp import server, types
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.server import sse

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
load_dotenv()


async def create_gateway_server(remote_app: ClientSession) -> server.Server[object]:
    """Create a server instance from a remote app."""
    logger.debug("Sending initialization request to remote MCP server...")
    response = await remote_app.initialize()
    capabilities = response.capabilities

    logger.debug("Configuring proxied MCP server...")
    app: server.Server[object] = server.Server(name=response.serverInfo.name)

    if capabilities.prompts:
        logger.debug("Capabilities: adding Prompts...")

        async def _list_prompts(_: t.Any) -> types.ServerResult:  # noqa: ANN401
            result = await remote_app.list_prompts()
            return types.ServerResult(result)

        app.request_handlers[types.ListPromptsRequest] = _list_prompts

        async def _get_prompt(req: types.GetPromptRequest) -> types.ServerResult:
            result = await remote_app.get_prompt(req.params.name, req.params.arguments)
            return types.ServerResult(result)

        app.request_handlers[types.GetPromptRequest] = _get_prompt

    if capabilities.resources:
        logger.debug("Capabilities: adding Resources...")

        async def _list_resources(_: t.Any) -> types.ServerResult:  # noqa: ANN401
            result = await remote_app.list_resources()
            return types.ServerResult(result)

        app.request_handlers[types.ListResourcesRequest] = _list_resources

        async def _list_resource_templates(_: t.Any) -> types.ServerResult:  # noqa: ANN401
            result = await remote_app.list_resource_templates()
            return types.ServerResult(result)

        app.request_handlers[types.ListResourceTemplatesRequest] = _list_resource_templates

        async def _read_resource(req: types.ReadResourceRequest) -> types.ServerResult:
            result = await remote_app.read_resource(req.params.uri)
            return types.ServerResult(result)

        app.request_handlers[types.ReadResourceRequest] = _read_resource

    if capabilities.logging:
        logger.debug("Capabilities: adding Logging...")

        async def _set_logging_level(req: types.SetLevelRequest) -> types.ServerResult:
            await remote_app.set_logging_level(req.params.level)
            return types.ServerResult(types.EmptyResult())

        app.request_handlers[types.SetLevelRequest] = _set_logging_level

    if capabilities.resources:
        logger.debug("Capabilities: adding Resources...")

        async def _subscribe_resource(req: types.SubscribeRequest) -> types.ServerResult:
            await remote_app.subscribe_resource(req.params.uri)
            return types.ServerResult(types.EmptyResult())

        app.request_handlers[types.SubscribeRequest] = _subscribe_resource

        async def _unsubscribe_resource(req: types.UnsubscribeRequest) -> types.ServerResult:
            await remote_app.unsubscribe_resource(req.params.uri)
            return types.ServerResult(types.EmptyResult())

        app.request_handlers[types.UnsubscribeRequest] = _unsubscribe_resource

    if capabilities.tools:
        logger.debug("Capabilities: adding Tools...")

        async def _list_tools(_: t.Any) -> types.ServerResult:
            try:  # noqa: ANN401
                tools = await remote_app.list_tools()
                return types.ServerResult(tools)
            except Exception as e:
                print(e)

        app.request_handlers[types.ListToolsRequest] = _list_tools

        async def _call_tool(req: types.CallToolRequest) -> types.ServerResult:
            try:
                result = await remote_app.call_tool(
                    req.params.name,
                    (req.params.arguments or {}),
                )
                return types.ServerResult(result)
            except Exception as e:  # noqa: BLE001
                return types.ServerResult(
                    types.CallToolResult(
                        content=[types.TextContent(type="text", text=str(e))],
                        isError=True,
                    ),
                )

        app.request_handlers[types.CallToolRequest] = _call_tool

    async def _send_progress_notification(req: types.ProgressNotification) -> None:
        await remote_app.send_progress_notification(
            req.params.progressToken,
            req.params.progress,
            req.params.total,
        )

    app.notification_handlers[types.ProgressNotification] = _send_progress_notification

    async def _complete(req: types.CompleteRequest) -> types.ServerResult:
        result = await remote_app.complete(
            req.params.ref,
            req.params.argument.model_dump(),
        )
        return types.ServerResult(result)

    app.request_handlers[types.CompleteRequest] = _complete

    return app



async def expose_available_tools(request: Request) -> JSONResponse:
    gateway_app = getattr(request.app.state, "gateway_app", None)
    if not gateway_app:
        return JSONResponse({"error": "Gateway not initialized"}, status_code=503)

    try:
        tools_result = await gateway_app.request_handlers[types.ListToolsRequest](None)
        return JSONResponse(tools_result.model_dump_json())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def run_gateway(remote_url: str, headers: dict[str, str] | None = None):
    async with streamablehttp_client(url=remote_url, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as remote_session:

            gateway_app = await create_gateway_server(remote_session)


            mcp_transport = sse.SseServerTransport("/messages/")

            async def handle_sse(request: Request):
                async with mcp_transport.connect_sse(request.scope, request.receive, request._send) as (read_sse, write_sse):
                    await gateway_app.run(read_sse, write_sse, gateway_app.create_initialization_options())
                return Response()


            api_app = Starlette(routes=[
                Route("/tools", expose_available_tools, methods=["GET"])
            ])
            
            api_app.state.gateway_app = gateway_app


            app = Starlette(routes=[
                Route("/sse", endpoint=handle_sse),
                Mount("/messages/", app=mcp_transport.handle_post_message),
                Mount("/config", app=api_app)
            ])


            config = uvicorn.Config(app, host="127.0.0.1", port=9000, log_level="info")
            server = uvicorn.Server(config)
            await server.serve()


if __name__ == "__main__":
    github_mcp_url = "https://api.githubcopilot.com/mcp"
    github_auth_token = os.environ.get("GITHUB_AUTH_TOKEN")
    if not github_auth_token:
        raise RuntimeError("GITHUB_AUTH_TOKEN environment variable is missing!")
    asyncio.run(run_gateway(github_mcp_url, headers={"Authorization": f"Bearer {github_auth_token}"}))
