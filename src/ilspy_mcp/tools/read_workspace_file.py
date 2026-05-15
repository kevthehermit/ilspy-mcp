"""read_workspace_file — read a text file from the workspace, with byte paging."""
from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .. import workspace

_DEFAULT_MAX = 200_000  # 200 KB
_BINARY_EXTS = {".dll", ".exe", ".pdb", ".so", ".dylib", ".bin", ".zip", ".tar", ".gz"}


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def read_workspace_file(
        path: str,
        max_bytes: int = _DEFAULT_MAX,
        offset_bytes: int = 0,
        encoding: str = "utf-8",
    ) -> dict[str, Any]:
        """Read (a slice of) a text file from the workspace.

        Use for notes, decompiled `.cs` output, configs, etc. Refuses to read
        known-binary extensions; for assemblies use `decompile_*`.

        For files larger than `max_bytes`, paginate by setting `offset_bytes`
        to the previous response's `next_offset_bytes` and calling again.

        Args:
            path: File path relative to the workspace root.
            max_bytes: Read at most this many bytes per call. Default 200_000.
            offset_bytes: Start reading at this byte offset (default 0).
            encoding: Text encoding (default utf-8).
        """
        p = workspace.resolve(path)
        if not p.is_file():
            raise ValueError(f"not a file: {path}")
        if p.suffix.lower() in _BINARY_EXTS:
            raise ValueError(
                f"refusing to read binary file ({p.suffix}); use decompile_* for assemblies"
            )

        size = p.stat().st_size
        if offset_bytes < 0 or offset_bytes > size:
            raise ValueError(f"offset_bytes {offset_bytes} out of range [0, {size}]")

        with p.open("rb") as f:
            f.seek(offset_bytes)
            data = f.read(max_bytes)

        end_offset = offset_bytes + len(data)
        truncated = end_offset < size

        try:
            content = data.decode(encoding)
        except UnicodeDecodeError as e:
            raise ValueError(
                f"file is not valid {encoding} (try paging on a chunk boundary): {e}"
            ) from None

        return {
            "path": workspace.relpath(p),
            "size_bytes": size,
            "offset_bytes": offset_bytes,
            "bytes_read": len(data),
            "truncated": truncated,
            "next_offset_bytes": end_offset if truncated else None,
            "content": content,
        }
