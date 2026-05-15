# ilspy-mcp

MCP server that exposes [ILSpy](https://github.com/icsharpcode/ILSpy) .NET decompilation as tools over HTTP, so an LLM client can triage and reverse-engineer .NET binaries (DLL/EXE) you drop into a workspace folder.

- HTTP transport (streamable-http) — works behind `mcp-remote` or any MCP HTTP client.
- OpenAPI front-end via [mcpo](https://github.com/open-webui/mcpo) — every tool is also a REST endpoint with Swagger docs (great for OpenWebUI, custom GPT actions, etc.).
- Linux + Docker first-class.
- Wraps the official `ilspycmd` global tool (v10.x).
- Sandboxed file access: every tool path is resolved under a single `ILSPY_WORKSPACE` directory.
- Static bearer-token auth.

## Tools

| Tool | Purpose |
|---|---|
| `list_workspace` | List every file/dir in the workspace (notes, configs, decompile output). |
| `list_assemblies` | List `.dll`/`.exe` files in the workspace. |
| `get_assembly_info` | Assembly + module metadata for one binary. |
| `list_types` | Fully-qualified type names in an assembly. |
| `list_members` | Methods / fields / properties / events of a type. |
| `decompile_type` | C# source for one type (optionally with IL). |
| `decompile_method` | C# source for one method within a type. |
| `decompile_assembly` | Full project tree (inline if small, otherwise paths). |
| `search_strings` | Grep across the decompiled C# source. |
| `read_workspace_file` | Read a text file from the workspace (notes, decompiled `.cs`, configs). |
| `write_workspace_file` | Write/append a text file (e.g. `progress.md`, `findings.md`). Refuses to clobber binaries. |

All `assembly` arguments are paths **relative to the workspace root**.

## Quickstart (Docker)

```bash
echo "MCP_AUTH_TOKEN=$(openssl rand -hex 32)" > .env
mkdir -p workspace && cp /path/to/your.dll workspace/
docker compose up --build -d
```

Or skip the build and pull a pre-built image from GHCR (published by the `Build and publish image` GitHub Action):

| Tag | Source |
|---|---|
| `ghcr.io/<owner>/ilspy-mcp:main` | tip of the `main` branch (rolling) |
| `ghcr.io/<owner>/ilspy-mcp:latest` | most recent `vX.Y.Z` tag |
| `ghcr.io/<owner>/ilspy-mcp:1.2.3` | a specific release |

In `docker-compose.yml`, replace `build: .` with `image: ghcr.io/<owner>/ilspy-mcp:latest` to use a published image instead of building locally.

Then connect any MCP HTTP client:

```bash
npx mcp-remote http://localhost:8000/mcp \
  --header "Authorization: Bearer $MCP_AUTH_TOKEN"
```

### Claude Code config

Add to `~/.claude.json` (or your project `.mcp.json`) under `mcpServers`. Replace the host/port with where the server is reachable, and substitute the token from your `.env`:

```json
{
  "mcpServers": {
    "ilspy": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://127.0.0.1:8000/mcp",
        "--allow-http",
        "--header",
        "Authorization: Bearer ${MCP_AUTH_TOKEN}"
      ],
      "env": {
        "MCP_AUTH_TOKEN": "paste-token-here"
      }
    }
  }
}
```

`--allow-http` is required because `mcp-remote` defaults to HTTPS-only. Drop it if you front the server with TLS.

### OpenAPI / REST (mcpo)

`docker compose up` also brings up an [mcpo](https://github.com/open-webui/mcpo) sidecar on port **8001** that exposes every MCP tool as a REST endpoint with Swagger docs:

```
http://localhost:8001/docs           # interactive Swagger UI
http://localhost:8001/openapi.json   # OpenAPI schema
http://localhost:8001/decompile_type # one endpoint per tool
```

Auth uses the same `MCP_AUTH_TOKEN` as the MCP front:

```bash
curl -X POST http://localhost:8001/list_assemblies \
  -H "Authorization: Bearer $MCP_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

Drop the `mcpo` service from `docker-compose.yml` if you don't need it.

## Quickstart (local, no Docker)

Requires Python 3.11+ and the .NET 9 SDK so `ilspycmd` can be installed:

```bash
dotnet tool install -g ilspycmd
export PATH="$HOME/.dotnet/tools:$PATH"

python -m venv .venv && source .venv/bin/activate
pip install -e .

export MCP_AUTH_TOKEN=devtoken
export ILSPY_WORKSPACE="$PWD/workspace"
python -m ilspy_mcp
```

Endpoint: `http://127.0.0.1:8000/mcp`.

## Configuration

| Env var | Default | Purpose |
|---|---|---|
| `MCP_AUTH_TOKEN` | *(required)* | Bearer token clients must present. Server refuses to start if unset. |
| `ILSPY_WORKSPACE` | `/workspace` | Root directory for assemblies. |
| `MCP_HOST` | `0.0.0.0` | Bind address. |
| `MCP_PORT` | `8000` | Bind port. |
| `ILSPYCMD_BIN` | `$(which ilspycmd)` | Override the path to the `ilspycmd` binary. |

## Security notes

- All tool paths are validated against `ILSPY_WORKSPACE`; symlinks and `..` traversal are rejected.
- Auth is a single static bearer token compared in constant time. For multi-tenant or public exposure, put the server behind a reverse proxy with stronger auth.
- `decompile_assembly` writes a per-assembly cache under `ILSPY_WORKSPACE/.ilspy-out/`. Mount the workspace read-write if you want this; otherwise mount read-only and cache misses just re-decompile each call.

## Development

```bash
pip install -e ".[dev]"
pytest
```
