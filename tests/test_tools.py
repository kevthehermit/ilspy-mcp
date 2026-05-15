"""Tool-level tests. ilspycmd is mocked so no .NET SDK is required."""
from __future__ import annotations

import asyncio

import pytest

from ilspy_mcp import cache as cache_mod
from ilspy_mcp.server import build_mcp


@pytest.fixture(autouse=True)
def reset_cache():
    cache_mod.clear()
    yield
    cache_mod.clear()


@pytest.fixture
def mcp():
    return build_mcp()


async def _call(mcp, name, **kwargs):
    res = await mcp.call_tool(name, kwargs)
    payload = res[1] if isinstance(res, tuple) else res
    if isinstance(payload, dict) and set(payload.keys()) == {"result"}:
        return payload["result"]
    return payload


# ---------- list_assemblies ----------

async def test_list_assemblies_finds_dll_and_exe(workspace, mcp):
    (workspace / "A.dll").write_bytes(b"x")
    (workspace / "sub").mkdir()
    (workspace / "sub" / "B.exe").write_bytes(b"x")
    (workspace / "ignore.txt").write_text("nope")

    items = await _call(mcp, "list_assemblies")
    paths = sorted(item["path"] for item in items)
    assert paths == ["A.dll", "sub/B.exe"]


async def test_list_assemblies_non_recursive(workspace, mcp):
    (workspace / "A.dll").write_bytes(b"x")
    (workspace / "sub").mkdir()
    (workspace / "sub" / "B.dll").write_bytes(b"x")

    items = await _call(mcp, "list_assemblies", recursive=False)
    assert [item["path"] for item in items] == ["A.dll"]


# ---------- decompile_type ----------

async def test_decompile_type_returns_inline_source(
    workspace, fake_assembly, mcp, monkeypatch
):
    expected = "public class Foo { public int Bar() => 1; }"

    async def fake_decompile(path, type_name, *, il=False):
        return expected

    monkeypatch.setattr(
        "ilspy_mcp.tools.decompile_type.ilspy.decompile_type", fake_decompile
    )
    res = await _call(mcp, "decompile_type", assembly="Sample.dll", type="Foo")
    assert res["spilled"] is False
    assert res["source"] == expected
    assert res["path"] is None
    assert res["type_name"] == "Foo"
    assert res["assembly"] == "Sample.dll"


async def test_decompile_type_spills_when_too_large(
    workspace, fake_assembly, mcp, monkeypatch
):
    big = "// big\n" + ("x" * 600_000)

    async def fake_decompile(path, type_name, *, il=False):
        return big

    monkeypatch.setattr(
        "ilspy_mcp.tools.decompile_type.ilspy.decompile_type", fake_decompile
    )
    res = await _call(mcp, "decompile_type", assembly="Sample.dll", type="Big.Class")
    assert res["spilled"] is True
    assert res["source"] is None
    assert res["path"].startswith(".ilspy-out/spilled/")
    assert res["preview"].startswith("// big")
    assert (workspace / res["path"]).read_text() == big
    assert res["next_steps"] and "read_workspace_file" in res["next_steps"]


async def test_decompile_type_caches(workspace, fake_assembly, mcp, monkeypatch):
    calls = 0

    async def fake_decompile(path, type_name, *, il=False):
        nonlocal calls
        calls += 1
        return "src"

    monkeypatch.setattr(
        "ilspy_mcp.tools.decompile_type.ilspy.decompile_type", fake_decompile
    )
    await _call(mcp, "decompile_type", assembly="Sample.dll", type="Foo")
    await _call(mcp, "decompile_type", assembly="Sample.dll", type="Foo")
    assert calls == 1


# ---------- list_types ----------

async def test_list_types_strips_kind_and_filters_namespace(
    workspace, fake_assembly, mcp, monkeypatch
):
    async def fake_run(args, *, cwd=None, timeout=120.0):
        return "Class Foo.Bar.A\nEnum Foo.Bar.B\nStruct Other.C\n"

    monkeypatch.setattr("ilspy_mcp.tools.list_types.ilspy.run", fake_run)
    items = await _call(mcp, "list_types", assembly="Sample.dll", namespace="Foo.Bar")
    assert items == ["Foo.Bar.A", "Foo.Bar.B"]


async def test_list_types_marks_nested_with_plus(
    workspace, fake_assembly, mcp, monkeypatch
):
    async def fake_run(args, *, cwd=None, timeout=120.0):
        return "Class Foo.Outer\nEnum Foo.Outer.Inner\n"

    monkeypatch.setattr("ilspy_mcp.tools.list_types.ilspy.run", fake_run)
    items = await _call(mcp, "list_types", assembly="Sample.dll")
    assert items == ["Foo.Outer", "Foo.Outer+Inner"]


# ---------- decompile_method ----------

async def test_decompile_method_extracts_one(workspace, fake_assembly, mcp, monkeypatch):
    source = """
public class Foo
{
    public int Bar() {
        return 1;
    }

    public string Baz(int x) {
        return x.ToString();
    }
}
""".strip()

    async def fake_decompile(path, type_name, *, il=False):
        return source

    monkeypatch.setattr(
        "ilspy_mcp.tools.decompile_method.ilspy.decompile_type", fake_decompile
    )
    res = await _call(
        mcp, "decompile_method", assembly="Sample.dll", type="Foo", method="Baz"
    )
    assert res["spilled"] is False
    assert res["method"] == "Baz"
    assert "Baz" in res["source"]
    assert "x.ToString()" in res["source"]
    assert "Bar()" not in res["source"]


async def test_decompile_method_missing(workspace, fake_assembly, mcp, monkeypatch):
    async def fake_decompile(path, type_name, *, il=False):
        return "public class Foo { }"

    monkeypatch.setattr(
        "ilspy_mcp.tools.decompile_method.ilspy.decompile_type", fake_decompile
    )
    with pytest.raises(Exception):
        await _call(
            mcp, "decompile_method", assembly="Sample.dll", type="Foo", method="Nope"
        )


# ---------- traversal protection at the tool boundary ----------

async def test_decompile_type_rejects_traversal(workspace, mcp):
    with pytest.raises(Exception):
        await _call(mcp, "decompile_type", assembly="../etc/passwd", type="Foo")
