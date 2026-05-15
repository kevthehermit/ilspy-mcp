"""list_members — extract members of a type from its decompiled C# source."""
from __future__ import annotations

import re
from typing import Any

from mcp.server.fastmcp import FastMCP

from .. import cache, ilspy, workspace

_METHOD_RE = re.compile(
    r"^\s*(?:public|private|protected|internal|static|virtual|override|sealed|abstract|extern|async|unsafe|new|partial|\s)+\s+"
    r"(?P<ret>[\w\.\<\>\[\],\s\?]+?)\s+(?P<name>[\w_]+)\s*\([^;{]*\)\s*[;{]"
)
_FIELD_RE = re.compile(
    r"^\s*(?:public|private|protected|internal|static|readonly|const|volatile|\s)+\s+"
    r"(?P<type>[\w\.\<\>\[\],\s\?]+?)\s+(?P<name>[\w_]+)\s*[=;]"
)
_PROP_RE = re.compile(
    r"^\s*(?:public|private|protected|internal|static|virtual|override|sealed|abstract|\s)+\s+"
    r"(?P<type>[\w\.\<\>\[\],\s\?]+?)\s+(?P<name>[\w_]+)\s*\{\s*(?:get|set)"
)
_EVENT_RE = re.compile(
    r"^\s*(?:public|private|protected|internal|static|\s)+\s+event\s+"
    r"(?P<type>[\w\.\<\>\[\],\s\?]+?)\s+(?P<name>[\w_]+)\s*[;{]"
)


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def list_members(assembly: str, type: str) -> dict[str, Any]:
        """List methods, fields, properties, and events of a type.

        Args:
            assembly: Path to the assembly, relative to the workspace root.
            type: Fully-qualified type name (e.g. `My.Namespace.MyClass`).
        """
        path = workspace.resolve(assembly)
        args_key = ("decompile_type", type, False)
        source = cache.get(path, args_key)
        if source is None:
            source = await ilspy.decompile_type(path, type, il=False)
            cache.put(path, args_key, source)

        methods: list[dict[str, Any]] = []
        fields: list[dict[str, Any]] = []
        properties: list[dict[str, Any]] = []
        events: list[dict[str, Any]] = []

        for line in source.splitlines():
            if (m := _EVENT_RE.match(line)):
                events.append({"name": m.group("name"), "type": m.group("type").strip()})
                continue
            if (m := _PROP_RE.match(line)):
                properties.append({"name": m.group("name"), "type": m.group("type").strip()})
                continue
            if (m := _METHOD_RE.match(line)):
                methods.append(
                    {"name": m.group("name"), "return_type": m.group("ret").strip()}
                )
                continue
            if (m := _FIELD_RE.match(line)):
                fields.append({"name": m.group("name"), "type": m.group("type").strip()})

        return {
            "type_name": type,
            "methods": methods,
            "fields": fields,
            "properties": properties,
            "events": events,
        }
