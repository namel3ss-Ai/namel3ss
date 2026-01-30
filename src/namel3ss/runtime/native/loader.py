from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


_NATIVE_ENV = "N3_NATIVE"
_NATIVE_LIB_ENV = "N3_NATIVE_LIB"
_TRUTHY = {"1", "true", "yes", "on"}

_LIB: object | None = None
_LOAD_ATTEMPTED = False


def native_enabled() -> bool:
    value = os.getenv(_NATIVE_ENV, "")
    return value.strip().lower() in _TRUTHY


def native_library_path() -> Path | None:
    value = os.getenv(_NATIVE_LIB_ENV, "").strip()
    if not value:
        return None
    return Path(value)


def load_library() -> object | None:
    global _LIB, _LOAD_ATTEMPTED
    if _LOAD_ATTEMPTED:
        return _LIB
    _LOAD_ATTEMPTED = True
    if not native_enabled():
        return None
    path = native_library_path()
    if path is None:
        return None
    if not path.exists():
        return None
    try:
        import ctypes

        _LIB = ctypes.CDLL(str(path))
    except OSError:
        _LIB = None
    return _LIB


def native_available() -> bool:
    return load_library() is not None


def _reset_native_state() -> None:
    global _LIB, _LOAD_ATTEMPTED
    _LIB = None
    _LOAD_ATTEMPTED = False


__all__ = [
    "load_library",
    "native_available",
    "native_enabled",
    "native_library_path",
]
