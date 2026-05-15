"""Sandboxed path resolution against the ILSPY_WORKSPACE root."""
from __future__ import annotations

import os
from pathlib import Path


class WorkspaceError(ValueError):
    """Raised when a path escapes the workspace root or cannot be resolved."""


def workspace_root() -> Path:
    return Path(os.environ.get("ILSPY_WORKSPACE", "/workspace")).resolve()


def resolve(rel: str, *, must_exist: bool = True) -> Path:
    """Resolve `rel` against the workspace root, rejecting traversal/escape."""
    if not rel or rel.strip() == "":
        raise WorkspaceError("path is empty")

    root = workspace_root()
    candidate = (root / rel) if not os.path.isabs(rel) else Path(rel)

    try:
        resolved = candidate.resolve(strict=must_exist)
    except FileNotFoundError as e:
        raise WorkspaceError(f"path not found: {rel}") from e

    if not resolved.is_relative_to(root):
        raise WorkspaceError(f"path escapes workspace: {rel}")

    return resolved


def relpath(p: Path) -> str:
    """Return `p` relative to the workspace root, for stable output."""
    return str(p.relative_to(workspace_root()))
