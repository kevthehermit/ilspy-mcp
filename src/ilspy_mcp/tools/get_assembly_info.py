"""get_assembly_info — extract assembly + module attribute lines from full decompile."""
from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .. import cache, ilspy, workspace

# A typical decompile starts with `using …;` lines, then `[assembly: …]` and
# optional `[module: …]` attributes, then `namespace …`. We grab the attribute
# block before the first `namespace`/type declaration.
_STOP_TOKENS = ("namespace ", "internal ", "public ", "[type:", "class ", "struct ", "enum ")


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def get_assembly_info(assembly: str) -> dict[str, Any]:
        """Return assembly and module metadata for a .NET binary.

        Args:
            assembly: Path to the assembly, relative to the workspace root.
        """
        path = workspace.resolve(assembly)
        args_key = ("info",)
        cached = cache.get(path, args_key)
        if cached is not None:
            return cached

        # Full decompile to stdout — header includes [assembly:…] / [module:…].
        raw = await ilspy.run([str(path)])

        assembly_attrs: list[str] = []
        module_attrs: list[str] = []
        for line in raw.splitlines():
            s = line.strip()
            if not s:
                continue
            if s.startswith("[assembly:"):
                assembly_attrs.append(s)
                continue
            if s.startswith("[module:"):
                module_attrs.append(s)
                continue
            if any(s.startswith(t) for t in _STOP_TOKENS):
                break

        info = {
            "path": workspace.relpath(path),
            "size_bytes": path.stat().st_size,
            "assembly_attributes": assembly_attrs,
            "module_attributes": module_attrs,
        }
        cache.put(path, args_key, info)
        return info
