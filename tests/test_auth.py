from __future__ import annotations

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from ilspy_mcp.auth import BearerAuthMiddleware, require_token


def _app(token: str) -> Starlette:
    async def ok(_): return PlainTextResponse("ok")
    async def health(_): return PlainTextResponse("up")
    app = Starlette(routes=[Route("/mcp", ok), Route("/health", health)])
    app.add_middleware(BearerAuthMiddleware, token=token)
    return app


def test_missing_token_rejected():
    client = TestClient(_app("secret"))
    r = client.get("/mcp")
    assert r.status_code == 401
    assert r.json()["reason"] == "missing bearer token"


def test_wrong_token_rejected():
    client = TestClient(_app("secret"))
    r = client.get("/mcp", headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401
    assert r.json()["reason"] == "invalid bearer token"


def test_correct_token_passes():
    client = TestClient(_app("secret"))
    r = client.get("/mcp", headers={"Authorization": "Bearer secret"})
    assert r.status_code == 200


def test_unprotected_path_passes_without_token():
    client = TestClient(_app("secret"))
    r = client.get("/health")
    assert r.status_code == 200


def test_require_token_fails_when_unset(monkeypatch):
    monkeypatch.delenv("MCP_AUTH_TOKEN", raising=False)
    with pytest.raises(SystemExit):
        require_token()


def test_require_token_fails_when_blank(monkeypatch):
    monkeypatch.setenv("MCP_AUTH_TOKEN", "   ")
    with pytest.raises(SystemExit):
        require_token()
