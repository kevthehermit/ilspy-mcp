"""list_types — enumerate types via `ilspycmd -l type`."""
from __future__ import annotations

import re

from mcp.server.fastmcp import FastMCP

from .. import cache, ilspy, workspace

# `ilspycmd -l type` emits lines like `Class Foo.Bar`, `Enum X.Y`, `Struct ...`.
_KIND_PREFIX = re.compile(
    r"^(?:Class|Struct|Interface|Enum|Delegate|Module|Type)\s+", re.IGNORECASE
)


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def list_types(assembly: str, namespace: str = "") -> list[str]:
        """List fully-qualified type names defined in the assembly.

        Args:
            assembly: Path to the assembly, relative to the workspace root.
            namespace: If set, only return types whose FQN starts with this prefix.
        """
        path = workspace.resolve(assembly)
        args_key = ("list_types",)
        types = cache.get(path, args_key)
        if types is None:
            raw = await ilspy.run(
                [str(path), "-l", "class,struct,interface,enum,delegate"]
            )
            raw_names: list[str] = []
            for ln in raw.splitlines():
                s = ln.strip()
                if not s:
                    continue
                stripped = _KIND_PREFIX.sub("", s)
                if stripped == s:
                    continue  # not a kind-prefixed line, skip noise
                raw_names.append(stripped)

            # Mark nested types by replacing the last `.` with `+` when the
            # prefix matches another listed (non-namespace) type.
            top_level = set(raw_names)
            types = []
            for n in raw_names:
                fixed = n
                while "." in fixed:
                    head, _, tail = fixed.rpartition(".")
                    head_fixed = head.replace(".", "+") if "+" in head else head
                    if head in top_level or head_fixed in top_level:
                        fixed = head + "+" + tail
                        # re-check: head itself might be nested
                        if "." in head and (head in top_level):
                            # one more pass: try further nesting
                            inner_head, _, inner_tail = head.rpartition(".")
                            if inner_head in top_level:
                                fixed = inner_head + "+" + inner_tail + "+" + tail
                        break
                    break
                types.append(fixed)
            cache.put(path, args_key, types)

        if namespace:
            prefix = namespace.rstrip(".") + "."
            return [t for t in types if t.startswith(prefix) or t == namespace]
        return types
