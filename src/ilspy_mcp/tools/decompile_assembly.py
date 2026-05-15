"""decompile_assembly — full project tree via `ilspycmd -p -o <tmpdir>`."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .. import cache, chunking, ilspy, workspace

_OUT_SUBDIR = ".ilspy-out"


def _output_dir(asm_path: Path) -> Path:
    root = workspace.workspace_root() / _OUT_SUBDIR
    h = hashlib.sha1(
        f"{asm_path}|{asm_path.stat().st_mtime_ns}|{asm_path.stat().st_size}".encode()
    ).hexdigest()[:12]
    out = root / f"{asm_path.stem}-{h}"
    out.mkdir(parents=True, exist_ok=True)
    return out


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def decompile_assembly(
        assembly: str,
        max_inline_bytes: int = chunking.DEFAULT_INLINE_LIMIT,
    ) -> dict[str, Any]:
        """Decompile an entire assembly to a C# project tree.

        Always writes the project under `.ilspy-out/<assembly>-<hash>/`. If the
        total size is at or below `max_inline_bytes` *and* every individual
        file fits in the inline limit, the contents are also returned inline.
        Otherwise just the file list + paths come back; read individual files
        with `read_workspace_file`.

        Args:
            assembly: Path to the assembly, relative to the workspace root.
            max_inline_bytes: Inline contents only if the total fits in this
                budget. Default ~400 KB to stay under common 1 MB MCP limits.
        """
        path = workspace.resolve(assembly)
        args_key = ("decompile_assembly",)
        cached = cache.get(path, args_key)
        if cached is not None:
            out_dir = Path(cached)
        else:
            out_dir = _output_dir(path)
            await ilspy.run([str(path), "-p", "-o", str(out_dir)])
            cache.put(path, args_key, str(out_dir))

        files: list[dict[str, Any]] = []
        total = 0
        for p in sorted(out_dir.rglob("*")):
            if not p.is_file():
                continue
            sz = p.stat().st_size
            total += sz
            files.append({"path": workspace.relpath(p), "size_bytes": sz})

        result: dict[str, Any] = {
            "assembly": workspace.relpath(path),
            "output_dir": workspace.relpath(out_dir),
            "files": files,
            "total_bytes": total,
        }

        if total <= max_inline_bytes:
            inline = []
            for f in files:
                fp = workspace.workspace_root() / f["path"]
                try:
                    inline.append(
                        {"path": f["path"], "content": fp.read_text(encoding="utf-8")}
                    )
                except UnicodeDecodeError:
                    inline.append({"path": f["path"], "content": None, "binary": True})
            result["inline_sources"] = inline

        return result
