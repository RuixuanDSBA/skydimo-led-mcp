"""
Skydimo MCP Server — makes LED strip controllable via Model Context Protocol.
Exposes tools and resources for AI coding tools to sync physical LED status.

Usage:
  python server.py          # stdio transport (for opencode/host MCP client)
  python server.py --http   # SSE HTTP transport (for debugging)
"""
import sys
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool, TextContent, Resource, ResourceTemplate,
    CallToolResult, ListToolsResult, ListResourcesResult,
    ReadResourceResult,
)

import skydimo_bridge as bridge


server = Server("skydimo-led")


# ─── Tools ───────────────────────────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> ListToolsResult:
    return ListToolsResult(tools=[
        Tool(
            name="set_led_state",
            description="Set the Skydimo LED strip to a visual state. "
                        "Modes: reasoning (rainbow), output (green chase), "
                        "decision (red pulse), idle (teal breathe), "
                        "waiting_user (teal+sparkle), testing (blue-white scan), "
                        "success (green wave), error (red double-pulse), "
                        "planning (purple breathe), git_push (yellow flash), "
                        "git_merge (orange pulse), off.",
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": list(bridge.VALID_MODES),
                        "description": "LED effect mode name",
                    }
                },
                "required": ["mode"],
            },
        ),
        Tool(
            name="start_daemon",
            description="Start the background LED daemon (optional initial mode).",
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": list(bridge.VALID_MODES),
                        "description": "Initial mode (default: idle)",
                    }
                },
            },
        ),
        Tool(
            name="stop_daemon",
            description="Gracefully stop the background LED daemon (sends off frame).",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_status",
            description="Get current daemon status, LED state, and Skydimo app status.",
            inputSchema={"type": "object", "properties": {}},
        ),
    ])


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    if name == "set_led_state":
        mode = arguments.get("mode", "")
        result = bridge.set_led_state(mode)
        return CallToolResult(content=[TextContent(type="text", text=result)])

    elif name == "start_daemon":
        mode = arguments.get("mode", "idle")
        result = bridge.start_daemon(mode)
        return CallToolResult(content=[TextContent(type="text", text=result)])

    elif name == "stop_daemon":
        result = bridge.stop_daemon()
        return CallToolResult(content=[TextContent(type="text", text=result)])

    elif name == "get_status":
        status = bridge.get_status()
        text = (
            f"Daemon: {status['daemon']}\n"
            f"Skydimo App: {status['skydimo_app']}\n"
            f"LED State: {status['state']}"
        )
        return CallToolResult(content=[TextContent(type="text", text=text)])

    else:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Unknown tool: {name}")],
            isError=True,
        )


# ─── Resources ───────────────────────────────────────────────────────────────

@server.list_resources()
async def list_resources() -> ListResourcesResult:
    return ListResourcesResult(resources=[
        Resource(
            uri="skydimo://status",
            name="Current LED Status",
            description="Current daemon status and LED state",
            mimeType="text/plain",
        ),
        Resource(
            uri="skydimo://modes",
            name="Available LED Modes",
            description="List of all valid LED effect modes",
            mimeType="application/json",
        ),
        Resource(
            uri="skydimo://help",
            name="Skydimo LED Help",
            description="Human-readable documentation for the Skydimo LED system",
            mimeType="text/html",
        ),
    ])


@server.read_resource()
async def read_resource(uri: str) -> ReadResourceResult:
    if uri == "skydimo://status":
        status = bridge.get_status()
        text = (
            f"Daemon: {status['daemon']}\n"
            f"Skydimo App: {status['skydimo_app']}\n"
            f"LED State: {status['state']}"
        )
        return ReadResourceResult(content=text.encode())

    elif uri == "skydimo://modes":
        modes = bridge.get_available_modes()
        return ReadResourceResult(content=json.dumps(modes, indent=2).encode())

    elif uri == "skydimo://help":
        import os as _os
        help_path = _os.path.join(_os.path.dirname(__file__), "index.html")
        if _os.path.exists(help_path):
            with open(help_path, "r", encoding="utf-8") as f:
                return ReadResourceResult(content=f.read().encode())
        return ReadResourceResult(content=b"<html><body><h1>Skydimo LED MCP</h1><p>Help file not found.</p></body></html>")

    else:
        return ReadResourceResult(content=f"Unknown resource: {uri}".encode())


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    import anyio
    async def _run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
    anyio.run(_run)


if __name__ == "__main__":
    main()
