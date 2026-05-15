"""Tests for list_workspace / read_workspace_file / write_workspace_file."""
from __future__ import annotations

import pytest

from ilspy_mcp.server import build_mcp


@pytest.fixture
def mcp():
    return build_mcp()


async def _call(mcp, name, **kwargs):
    res = await mcp.call_tool(name, kwargs)
    payload = res[1] if isinstance(res, tuple) else res
    # FastMCP wraps non-dict tool returns under {"result": ...}; dict returns
    # are exposed as-is.
    if isinstance(payload, dict) and set(payload.keys()) == {"result"}:
        return payload["result"]
    return payload


# ---------- list_workspace ----------

async def test_list_workspace_includes_non_assemblies(workspace, mcp):
    (workspace / "notes.md").write_text("hello")
    (workspace / "Sample.dll").write_bytes(b"x")
    (workspace / "sub").mkdir()
    (workspace / "sub" / "deep.txt").write_text("deep")

    items = await _call(mcp, "list_workspace")
    paths = sorted(i["path"] for i in items)
    assert "notes.md" in paths
    assert "Sample.dll" in paths
    assert "sub" in paths
    assert "sub/deep.txt" in paths


async def test_list_workspace_glob_pattern(workspace, mcp):
    (workspace / "notes.md").write_text("a")
    (workspace / "findings.md").write_text("b")
    (workspace / "Sample.dll").write_bytes(b"x")

    items = await _call(mcp, "list_workspace", pattern="*.md")
    names = sorted(i["path"] for i in items)
    assert names == ["findings.md", "notes.md"]


async def test_list_workspace_excludes_cache_by_default(workspace, mcp):
    cache = workspace / ".ilspy-out" / "x"
    cache.mkdir(parents=True)
    (cache / "out.cs").write_text("class X{}")
    (workspace / "notes.md").write_text("n")

    items = await _call(mcp, "list_workspace")
    paths = [i["path"] for i in items]
    assert "notes.md" in paths
    assert all(not p.startswith(".ilspy-out") for p in paths)

    items_with_cache = await _call(mcp, "list_workspace", include_cache=True)
    paths_with_cache = [i["path"] for i in items_with_cache]
    assert any(p.startswith(".ilspy-out") for p in paths_with_cache)


# ---------- read_workspace_file ----------

async def test_read_workspace_file(workspace, mcp):
    (workspace / "progress.md").write_text("hello world\n")
    res = await _call(mcp, "read_workspace_file", path="progress.md")
    assert res["content"] == "hello world\n"
    assert res["truncated"] is False
    assert res["size_bytes"] == 12


async def test_read_workspace_file_truncates(workspace, mcp):
    (workspace / "big.txt").write_text("a" * 1000)
    res = await _call(mcp, "read_workspace_file", path="big.txt", max_bytes=10)
    assert res["bytes_read"] == 10
    assert res["truncated"] is True
    assert res["content"] == "a" * 10
    assert res["next_offset_bytes"] == 10


async def test_read_workspace_file_paginates(workspace, mcp):
    (workspace / "log.txt").write_text("0123456789ABCDEFGHIJ")
    chunks = []
    offset = 0
    while True:
        res = await _call(
            mcp, "read_workspace_file", path="log.txt", max_bytes=7, offset_bytes=offset
        )
        chunks.append(res["content"])
        if not res["truncated"]:
            break
        offset = res["next_offset_bytes"]
    assert "".join(chunks) == "0123456789ABCDEFGHIJ"


async def test_read_workspace_file_offset_out_of_range(workspace, mcp):
    (workspace / "x.txt").write_text("hello")
    with pytest.raises(Exception):
        await _call(mcp, "read_workspace_file", path="x.txt", offset_bytes=999)


async def test_read_workspace_file_refuses_binary(workspace, mcp):
    (workspace / "Sample.dll").write_bytes(b"\x00\x01")
    with pytest.raises(Exception):
        await _call(mcp, "read_workspace_file", path="Sample.dll")


async def test_read_workspace_file_traversal(workspace, mcp):
    with pytest.raises(Exception):
        await _call(mcp, "read_workspace_file", path="../etc/passwd")


# ---------- write_workspace_file ----------

async def test_write_workspace_file_overwrite(workspace, mcp):
    res = await _call(
        mcp, "write_workspace_file", path="notes.md", content="first\n"
    )
    assert res["bytes_written"] == 6
    assert (workspace / "notes.md").read_text() == "first\n"

    await _call(mcp, "write_workspace_file", path="notes.md", content="second\n")
    assert (workspace / "notes.md").read_text() == "second\n"


async def test_write_workspace_file_append(workspace, mcp):
    await _call(mcp, "write_workspace_file", path="log.md", content="line1\n")
    await _call(
        mcp, "write_workspace_file", path="log.md", content="line2\n", mode="append"
    )
    assert (workspace / "log.md").read_text() == "line1\nline2\n"


async def test_write_workspace_file_creates_parent_dirs(workspace, mcp):
    await _call(
        mcp,
        "write_workspace_file",
        path="findings/luxnet/notes.md",
        content="x",
    )
    assert (workspace / "findings" / "luxnet" / "notes.md").read_text() == "x"


async def test_write_workspace_file_refuses_binary_extension(workspace, mcp):
    with pytest.raises(Exception):
        await _call(
            mcp, "write_workspace_file", path="bad.dll", content="not a binary"
        )


async def test_write_workspace_file_refuses_cache_dir(workspace, mcp):
    with pytest.raises(Exception):
        await _call(
            mcp,
            "write_workspace_file",
            path=".ilspy-out/clobber.cs",
            content="x",
        )


async def test_write_workspace_file_traversal(workspace, mcp):
    with pytest.raises(Exception):
        await _call(
            mcp, "write_workspace_file", path="../escape.md", content="x"
        )
