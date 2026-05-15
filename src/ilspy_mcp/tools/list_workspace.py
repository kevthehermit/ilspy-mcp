"""list_workspace — recursive listing of every file in the workspace."""
from __future__ import annotations

import fnmatch
from datetime import datetime, timezone
from typing import Any

from mcp.server.fastmcp import FastMCP

from .. import workspace

# Cache directory used by decompile_assembly — hidden by default to keep the
# listing focused on user content.
_CACHE_DIR = ".ilspy-out"


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def list_workspace(
        subdir: str = "",
        recursive: bool = True,
        pattern: str = "",
        include_dirs: bool = True,
        include_cache: bool = False,
    ) -> list[dict[str, Any]]:
        """List every file (and optionally directory) under the workspace.

        Use this to see notes, configs, decompiled output, and anything else
        that's not a .NET assembly. For just `.dll`/`.exe`, use `list_assemblies`.

        Args:
            subdir: Optional sub-path under the workspace root (default: root).
            recursive: Recurse into subdirectories (default: True).
            pattern: Glob pattern to filter names (e.g. `*.cs`, `notes*`). Empty = all.
            include_dirs: Include directories in the result (default: True).
            include_cache: Include the `.ilspy-out` decompile cache (default: False).
        """
        root = workspace.resolve(subdir) if subdir else workspace.workspace_root()
        if not root.is_dir():
            return []

        iterator = root.rglob("*") if recursive else root.iterdir()
        out: list[dict[str, Any]] = []
        for p in iterator:
            rel = workspace.relpath(p)

            # Skip the decompile cache unless asked.
            if not include_cache and (
                rel == _CACHE_DIR or rel.startswith(_CACHE_DIR + "/")
            ):
                continue

            if not include_dirs and p.is_dir():
                continue
            if pattern and not fnmatch.fnmatch(p.name, pattern):
                continue

            try:
                st = p.stat()
            except OSError:
                continue

            out.append(
                {
                    "path": rel,
                    "is_dir": p.is_dir(),
                    "size_bytes": st.st_size if p.is_file() else 0,
                    "modified": datetime.fromtimestamp(
                        st.st_mtime, tz=timezone.utc
                    ).isoformat(),
                }
            )
        out.sort(key=lambda r: r["path"])
        return out
