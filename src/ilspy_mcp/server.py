"""FastMCP server wiring: tools registration + ASGI app + bearer auth."""
from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette

from .auth import BearerAuthMiddleware, require_token
from .tools import register_all


def build_mcp() -> FastMCP:
    mcp = FastMCP(
        "ilspy",
        instructions=(
            "Decompile .NET assemblies (.dll/.exe) using ILSpy. "
            "All `assembly` arguments are paths relative to the workspace root."
        ),
        host=os.environ.get("MCP_HOST", "0.0.0.0"),
        port=int(os.environ.get("MCP_PORT", "8000")),
        stateless_http=True,
        json_response=True,
    )
    register_all(mcp)
    return mcp


def build_app(mcp: FastMCP | None = None) -> Starlette:
    """Return the ASGI app with bearer-auth middleware applied."""
    token = require_token()
    mcp = mcp or build_mcp()
    app = mcp.streamable_http_app()
    app.add_middleware(BearerAuthMiddleware, token=token)
    return app
