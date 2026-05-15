"""list_assemblies — filesystem scan for .dll/.exe under the workspace."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from mcp.server.fastmcp import FastMCP

from .. import workspace

_EXTS = {".dll", ".exe"}


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def list_assemblies(
        subdir: str = "",
        recursive: bool = True,
    ) -> list[dict[str, Any]]:
        """List .NET assemblies (.dll/.exe) found in the workspace.

        Args:
            subdir: Optional sub-path under the workspace root (default: root).
            recursive: Recurse into subdirectories (default: True).
        """
        root = workspace.resolve(subdir) if subdir else workspace.workspace_root()
        if not root.is_dir():
            return []

        iterator = root.rglob("*") if recursive else root.iterdir()
        out: list[dict[str, Any]] = []
        for p in iterator:
            if not p.is_file() or p.suffix.lower() not in _EXTS:
                continue
            st = p.stat()
            out.append(
                {
                    "path": workspace.relpath(p),
                    "size_bytes": st.st_size,
                    "modified": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
                }
            )
        out.sort(key=lambda r: r["path"])
        return out
