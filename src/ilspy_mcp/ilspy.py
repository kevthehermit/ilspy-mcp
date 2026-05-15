"""Thin async wrapper around the `ilspycmd` global tool."""
from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path


class IlspyCmdError(RuntimeError):
    pass


def _binary() -> str:
    override = os.environ.get("ILSPYCMD_BIN")
    if override:
        return override
    found = shutil.which("ilspycmd")
    if not found:
        raise IlspyCmdError(
            "ilspycmd not found on PATH; install with `dotnet tool install -g ilspycmd` "
            "or set ILSPYCMD_BIN."
        )
    return found


async def run(
    args: list[str],
    *,
    cwd: Path | None = None,
    timeout: float = 120.0,
) -> str:
    """Run `ilspycmd` with `args`, returning stdout. Raises on non-zero exit."""
    # `--disable-updatecheck` keeps update-warning text out of stdout.
    cmd = [_binary(), "--disable-updatecheck", *args]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(cwd) if cwd else None,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise IlspyCmdError(f"ilspycmd timed out after {timeout}s: {' '.join(args)}")

    if proc.returncode != 0:
        raise IlspyCmdError(
            f"ilspycmd exited {proc.returncode}: {stderr.decode('utf-8', 'replace').strip()}"
        )
    return stdout.decode("utf-8", "replace")


async def decompile_type(
    asm_path: Path,
    type_name: str,
    *,
    il: bool = False,
) -> str:
    """Decompile a single type, trying nested-type variants if the first attempt fails.

    `ilspycmd -t` requires `+` between an outer type and a nested type
    (`Outer+Inner`), but human-friendly names use `.`. We try the name as given,
    then progressively reinterpret trailing dots as nesting.
    """
    candidates = [type_name]
    if "." in type_name:
        parts = type_name.split(".")
        for cut in range(len(parts) - 1, 0, -1):
            candidates.append(".".join(parts[:cut]) + "+" + "+".join(parts[cut:]))

    last_err: IlspyCmdError | None = None
    for name in candidates:
        args = [str(asm_path), "-t", name]
        if il:
            args.append("-il")
        try:
            return await run(args)
        except IlspyCmdError as e:
            if "Could not find type" not in str(e):
                raise
            last_err = e
    assert last_err is not None
    raise last_err
