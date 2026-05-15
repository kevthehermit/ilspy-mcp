from __future__ import annotations

import pytest

from ilspy_mcp import workspace as ws


def test_resolves_relative_under_root(workspace, fake_assembly):
    p = ws.resolve("Sample.dll")
    assert p == fake_assembly


def test_rejects_traversal(workspace, fake_assembly):
    with pytest.raises(ws.WorkspaceError):
        ws.resolve("../etc/passwd")


def test_rejects_absolute_outside(workspace, fake_assembly):
    with pytest.raises(ws.WorkspaceError):
        ws.resolve("/etc/passwd")


def test_rejects_symlink_escape(workspace, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside") / "target.dll"
    outside.write_bytes(b"MZ")
    link = workspace / "link.dll"
    link.symlink_to(outside)
    with pytest.raises(ws.WorkspaceError):
        ws.resolve("link.dll")


def test_rejects_empty(workspace):
    with pytest.raises(ws.WorkspaceError):
        ws.resolve("")


def test_must_exist_default(workspace):
    with pytest.raises(ws.WorkspaceError):
        ws.resolve("nope.dll")
