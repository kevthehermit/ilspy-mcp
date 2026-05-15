"""decompile_type — decompile a single type to C# (optionally with IL)."""
from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .. import cache, chunking, ilspy, workspace


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def decompile_type(
        assembly: str, type: str, il: bool = False
    ) -> dict[str, Any]:
        """Decompile a single type to C# source code.

        Returns either inline `source` (small enough to fit a single MCP
        response) or `spilled=true` with a workspace-relative `path` to the
        full output and a `preview`. When spilled, follow the `next_steps`
        hint to read the file in chunks via `read_workspace_file`.

        Args:
            assembly: Path to the assembly, relative to the workspace root.
            type: Fully-qualified type name (e.g. `My.Namespace.MyClass`).
            il: If true, include IL code alongside the C# output.
        """
        path = workspace.resolve(assembly)
        args_key = ("decompile_type", type, il)
        source = cache.get(path, args_key)
        if source is None:
            source = await ilspy.decompile_type(path, type, il=il)
            cache.put(path, args_key, source)

        result = chunking.maybe_spill_text(
            source, name=f"{path.stem}-{type}{'-il' if il else ''}"
        )
        result["assembly"] = workspace.relpath(path)
        result["type_name"] = type
        return result
