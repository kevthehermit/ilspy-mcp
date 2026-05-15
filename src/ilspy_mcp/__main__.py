"""Entrypoint: `python -m ilspy_mcp` or the `ilspy-mcp` console script."""
from __future__ import annotations

import os

import uvicorn

from .server import build_app


def main() -> None:
    app = build_app()
    uvicorn.run(
        app,
        host=os.environ.get("MCP_HOST", "0.0.0.0"),
        port=int(os.environ.get("MCP_PORT", "8000")),
        log_level=os.environ.get("UVICORN_LOG_LEVEL", "info"),
    )


if __name__ == "__main__":
    main()
