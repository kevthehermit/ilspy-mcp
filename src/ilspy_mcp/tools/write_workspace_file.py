"""write_workspace_file — create / overwrite / append a text file in the workspace."""
from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from .. import workspace

# Extensions we refuse to clobber/append to — keep binaries and the cache safe.
_PROTECTED_EXTS = {".dll", ".exe", ".pdb", ".so", ".dylib"}
_PROTECTED_DIRS = (".ilspy-out",)


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def write_workspace_file(
        path: str,
        content: str,
        mode: Literal["overwrite", "append"] = "overwrite",
    ) -> dict[str, Any]:
        """Write a text file to the workspace.

        Use this to keep progress notes, findings, or analysis logs across
        sessions (e.g. `progress.md`, `findings/luxnet.md`). Parent directories
        are created automatically.

        Args:
            path: File path relative to the workspace root.
            content: UTF-8 text to write.
            mode: `overwrite` (default) or `append`.
        """
        # Resolve without requiring existence — this is a write.
        p = workspace.resolve(path, must_exist=False)

        if p.suffix.lower() in _PROTECTED_EXTS:
            raise ValueError(f"refusing to write protected extension: {p.suffix}")

        rel = workspace.relpath(p)
        if any(rel == d or rel.startswith(d + "/") for d in _PROTECTED_DIRS):
            raise ValueError(f"refusing to write into protected directory: {rel}")

        p.parent.mkdir(parents=True, exist_ok=True)

        if mode == "append":
            with p.open("a", encoding="utf-8") as f:
                bytes_written = f.write(content)
        else:
            with p.open("w", encoding="utf-8") as f:
                bytes_written = f.write(content)

        return {
            "path": rel,
            "mode": mode,
            "size_bytes": p.stat().st_size,
            "bytes_written": bytes_written,
        }
