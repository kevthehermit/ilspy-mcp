"""Tool registry — each module defines `register(mcp)`."""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import (
    decompile_assembly,
    decompile_method,
    decompile_type,
    get_assembly_info,
    list_assemblies,
    list_members,
    list_types,
    list_workspace,
    read_workspace_file,
    search_strings,
    write_workspace_file,
)

_modules = (
    list_workspace,
    list_assemblies,
    get_assembly_info,
    list_types,
    list_members,
    decompile_type,
    decompile_method,
    decompile_assembly,
    search_strings,
    read_workspace_file,
    write_workspace_file,
)


def register_all(mcp: FastMCP) -> None:
    for m in _modules:
        m.register(mcp)
