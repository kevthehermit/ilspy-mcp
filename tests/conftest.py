"""Test fixtures.

We don't depend on the .NET SDK being installed; tools that shell out to
ilspycmd are exercised by monkeypatching `ilspy_mcp.ilspy.run`.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture
def workspace(tmp_path, monkeypatch) -> Path:
    """Create a tmp workspace and point ILSPY_WORKSPACE at it."""
    monkeypatch.setenv("ILSPY_WORKSPACE", str(tmp_path))
    # `workspace.workspace_root()` re-reads the env each call, so no module reload needed.
    return tmp_path


@pytest.fixture
def fake_assembly(workspace) -> Path:
    """A non-empty file that looks like an assembly to filesystem checks."""
    p = workspace / "Sample.dll"
    p.write_bytes(b"MZ" + b"\x00" * 126)  # rough PE header
    return p
