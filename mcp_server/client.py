"""MCP client wrapper for the Customer Support MCP Server.

Provides two modes:
1. **In-process** (default): Connects via stdio to the MCP server script.
   No separate process needed - used by the LangGraph agent and tests.
2. **Remote**: Connects to an HTTP MCP server at a given URL.

The client converts MCP tools to LangChain-compatible tools using
langchain-mcp-adapters.
"""

import asyncio
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

_SERVER_SCRIPT = str(Path(__file__).resolve().parent / "server.py")
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)


@asynccontextmanager
async def get_mcp_session() -> AsyncIterator[ClientSession]:
    """Open a stdio MCP session to the support server."""
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[_SERVER_SCRIPT],
        env={"PYTHONPATH": _PROJECT_ROOT},
    )
    async with stdio_client(server_params) as (read_stream, write_stream), ClientSession(read_stream, write_stream) as session:
        await session.initialize()
        yield session


async def get_mcp_langchain_tools() -> list:
    """Load MCP tools as LangChain-compatible tools.

    Opens a session, discovers tools, wraps them, and returns.
    The caller should use these tools within the session context.
    """
    async with get_mcp_session() as session:
        tools = await load_mcp_tools(session)
        return tools


async def call_mcp_tool(tool_name: str, arguments: dict) -> str | dict:
    """Call a single MCP tool by name and return the result.

    This is the primary interface used by graph nodes - opens a session,
    calls the tool, and returns the parsed result.
    """
    async with get_mcp_session() as session:
        result = await session.call_tool(tool_name, arguments)
        # MCP returns a list of content blocks - extract the text
        if result.content:
            import json
            text = result.content[0].text
            try:
                return json.loads(text)
            except (json.JSONDecodeError, AttributeError):
                return text
        return {"error": "No content returned"}


async def list_mcp_resources(session: ClientSession) -> list[dict]:
    """List all available resources from the MCP server."""
    result = await session.list_resources()
    return [
        {"uri": str(r.uri), "name": r.name, "description": r.description}
        for r in result.resources
    ]


async def read_mcp_resource(session: ClientSession, uri: str) -> str:
    """Read a specific resource by URI."""
    result = await session.read_resource(uri)
    if result.contents:
        return result.contents[0].text
    return ""


def call_mcp_tool_sync(tool_name: str, arguments: dict) -> str | dict:
    """Synchronous wrapper around call_mcp_tool for use in graph nodes."""
    return asyncio.run(call_mcp_tool(tool_name, arguments))
