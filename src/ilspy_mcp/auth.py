"""Static-bearer-token ASGI middleware.

We wrap FastMCP's Starlette app with this rather than using the SDK's
TokenVerifier path, which is geared toward OAuth resource-server metadata
and would force us to declare an issuer URL we don't have.
"""
from __future__ import annotations

import hmac
import os

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class BearerAuthMiddleware:
    def __init__(self, app: ASGIApp, *, token: str, protected_prefix: str = "/mcp") -> None:
        if not token:
            raise ValueError("MCP_AUTH_TOKEN must be set (non-empty)")
        self.app = app
        self.token = token
        self.protected_prefix = protected_prefix

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith(self.protected_prefix):
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        auth = headers.get(b"authorization", b"").decode("latin-1")
        if not auth.lower().startswith("bearer "):
            await self._reject(scope, receive, send, "missing bearer token")
            return
        presented = auth[len("bearer "):].strip()
        if not hmac.compare_digest(presented, self.token):
            await self._reject(scope, receive, send, "invalid bearer token")
            return

        await self.app(scope, receive, send)

    @staticmethod
    async def _reject(scope: Scope, receive: Receive, send: Send, reason: str) -> None:
        resp = JSONResponse({"error": "unauthorized", "reason": reason}, status_code=401)
        await resp(scope, receive, send)


def require_token() -> str:
    token = os.environ.get("MCP_AUTH_TOKEN", "").strip()
    if not token:
        raise SystemExit(
            "MCP_AUTH_TOKEN env var is required (non-empty). Set it before starting the server."
        )
    return token
