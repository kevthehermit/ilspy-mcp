"""Spill large outputs to disk so they fit MCP transport limits.

The MCP wire format duplicates dict tool returns under both `content` (JSON
string) and `structuredContent`, so the on-the-wire size can be ~2x the dict
size. Most clients (Claude Code today) cap a single tool response at 1 MB.
We stay well under that and surface a stable file path the LLM can read in
chunks via `read_workspace_file` or grep via `search_strings`.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from . import workspace

# Conservative ceiling: leave headroom for the duplicate JSON envelope.
DEFAULT_INLINE_LIMIT = 400_000   # ~400 KB
DEFAULT_PREVIEW_BYTES = 4_000    # 4 KB visible preview when spilled

_SPILL_SUBDIR = ".ilspy-out/spilled"
_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._+-]")


def _safe_name(name: str) -> str:
    return _SAFE_NAME_RE.sub("_", name)[:120] or "out"


def maybe_spill_text(
    text: str,
    *,
    name: str,
    suffix: str = ".cs",
    inline_limit: int = DEFAULT_INLINE_LIMIT,
    preview_bytes: int = DEFAULT_PREVIEW_BYTES,
) -> dict[str, Any]:
    """Return a uniform dict either with inline `source` or a `path` to disk.

    Always returns the same shape so callers (and the LLM) don't have to
    branch on the type:

        {
          "source": str | None,           # None when spilled
          "size_bytes": int,
          "spilled": bool,
          "path": str | None,             # workspace-relative when spilled
          "preview": str | None,          # head of the file when spilled
          "next_steps": str | None,       # hint for the LLM when spilled
        }
    """
    encoded = text.encode("utf-8")
    size = len(encoded)

    if size <= inline_limit:
        return {
            "source": text,
            "size_bytes": size,
            "spilled": False,
            "path": None,
            "preview": None,
            "next_steps": None,
        }

    h = hashlib.sha1(encoded).hexdigest()[:12]
    out_dir = workspace.workspace_root() / _SPILL_SUBDIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out: Path = out_dir / f"{_safe_name(name)}-{h}{suffix}"
    out.write_bytes(encoded)

    return {
        "source": None,
        "size_bytes": size,
        "spilled": True,
        "path": workspace.relpath(out),
        "preview": text[:preview_bytes],
        "next_steps": (
            f"Output is {size} bytes (limit {inline_limit}). "
            f"Read the full file with read_workspace_file(path, offset_bytes=..., max_bytes=...) "
            f"or grep with search_strings."
        ),
    }
