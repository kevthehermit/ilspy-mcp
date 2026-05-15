"""decompile_method — slice one method out of a decompiled type."""
from __future__ import annotations

import re
from typing import Any

from mcp.server.fastmcp import FastMCP

from .. import cache, chunking, ilspy, workspace


def _extract_method(source: str, name: str) -> str | None:
    """Find the first method declaration matching `name` and return its body."""
    # match modifiers + return type + name + (...) up to opening { or ;
    pattern = re.compile(
        r"^(?P<indent>[ \t]*)"
        r"(?:(?:public|private|protected|internal|static|virtual|override|sealed|abstract|extern|async|unsafe|new|partial)\s+)+"
        r"[\w\.\<\>\[\],\s\?]+?\s+"
        + re.escape(name)
        + r"\s*\([^;{]*\)\s*[;{]",
        re.MULTILINE,
    )
    m = pattern.search(source)
    if not m:
        return None

    start = m.start()
    # find opening brace or semicolon
    body_start = source.find("{", m.end() - 1)
    semi = source.find(";", m.end() - 1)
    if body_start == -1 or (semi != -1 and semi < body_start):
        # abstract/extern/interface method ending in `;`
        end = (semi if semi != -1 else m.end()) + 1
        return source[start:end]

    depth = 0
    i = body_start
    while i < len(source):
        c = source[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return source[start : i + 1]
        i += 1
    return source[start:]  # unbalanced — return rest


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def decompile_method(
        assembly: str,
        type: str,
        method: str,
        il: bool = False,
    ) -> dict[str, Any]:
        """Decompile a single method by name within a type.

        Args:
            assembly: Path to the assembly, relative to the workspace root.
            type: Fully-qualified type name containing the method.
            method: Method name (overloads collapse to the first match).
            il: If true, include IL code alongside the C# output.
        """
        path = workspace.resolve(assembly)
        args_key = ("decompile_type", type, il)
        source = cache.get(path, args_key)
        if source is None:
            source = await ilspy.decompile_type(path, type, il=il)
            cache.put(path, args_key, source)

        snippet = _extract_method(source, method)
        if snippet is None:
            raise ValueError(f"method '{method}' not found in {type}")

        result = chunking.maybe_spill_text(
            snippet,
            name=f"{path.stem}-{type}-{method}{'-il' if il else ''}",
        )
        result["assembly"] = workspace.relpath(path)
        result["type_name"] = type
        result["method"] = method
        return result
