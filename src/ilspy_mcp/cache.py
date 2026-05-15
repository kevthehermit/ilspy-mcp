"""LRU cache keyed on (absolute path, mtime, args) for ilspycmd outputs."""
from __future__ import annotations

import hashlib
from collections import OrderedDict
from pathlib import Path
from typing import Any

_MAX_ENTRIES = 32
_store: "OrderedDict[str, Any]" = OrderedDict()


def _key(path: Path, args: tuple) -> str:
    st = path.stat()
    h = hashlib.sha1()
    h.update(str(path).encode())
    h.update(str(st.st_mtime_ns).encode())
    h.update(str(st.st_size).encode())
    h.update(repr(args).encode())
    return h.hexdigest()


def get(path: Path, args: tuple) -> Any | None:
    key = _key(path, args)
    if key in _store:
        _store.move_to_end(key)
        return _store[key]
    return None


def put(path: Path, args: tuple, value: Any) -> None:
    key = _key(path, args)
    _store[key] = value
    _store.move_to_end(key)
    while len(_store) > _MAX_ENTRIES:
        _store.popitem(last=False)


def clear() -> None:
    _store.clear()
