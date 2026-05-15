"""search_strings — grep across the decompiled project tree."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .. import cache, ilspy, workspace
from .decompile_assembly import _output_dir


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def search_strings(
        assembly: str,
        pattern: str,
        regex: bool = False,
        max_matches: int = 200,
    ) -> list[dict[str, Any]]:
        """Search the decompiled C# of an assembly for a literal or regex pattern.

        Args:
            assembly: Path to the assembly, relative to the workspace root.
            pattern: Substring to search (or regex if `regex=True`).
            regex: Treat `pattern` as a regular expression.
            max_matches: Stop after this many matches.
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

        if regex:
            rx = re.compile(pattern)
            def matches(line: str) -> bool: return bool(rx.search(line))
        else:
            needle = pattern
            def matches(line: str) -> bool: return needle in line

        results: list[dict[str, Any]] = []
        for fp in sorted(out_dir.rglob("*.cs")):
            try:
                text = fp.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                if matches(line):
                    results.append(
                        {
                            "file": workspace.relpath(fp),
                            "line": lineno,
                            "snippet": line.strip()[:400],
                        }
                    )
                    if len(results) >= max_matches:
                        return results
        return results
