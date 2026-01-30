from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
import os

from namel3ss.runtime.native.loader import native_library_path
from namel3ss.runtime.native.status import NativeStatus, status_from_int, status_to_code


_NATIVE_EXEC_ENV = "N3_NATIVE_EXEC"
_TRUTHY = {"1", "true", "yes", "on"}
_EXEC_LIB: object | None = None
_EXEC_LOAD_ATTEMPTED = False


@dataclass(frozen=True, slots=True)
class NativeOutcome:
    status: NativeStatus
    payload: bytes | None
    error_code: str | None

    def should_fallback(self) -> bool:
        return self.status != NativeStatus.OK


def native_exec_enabled() -> bool:
    value = os.getenv(_NATIVE_EXEC_ENV, "")
    return value.strip().lower() in _TRUTHY


def _outcome(status: NativeStatus, payload: bytes | None = None) -> NativeOutcome:
    code = status_to_code(status)
    if status != NativeStatus.OK:
        payload = None
    return NativeOutcome(status=status, payload=payload, error_code=code)


def _buffer_type():
    import ctypes

    class _Buffer(ctypes.Structure):
        _fields_ = [
            ("data", ctypes.POINTER(ctypes.c_ubyte)),
            ("len", ctypes.c_size_t),
        ]

    return _Buffer


def _configure_fn(fn: Callable, *, argtypes, restype) -> Callable:
    fn.argtypes = argtypes
    fn.restype = restype
    return fn


def _get_function(lib: object, name: str, *, argtypes, restype) -> Callable | None:
    fn = getattr(lib, name, None)
    if fn is None:
        return None
    return _configure_fn(fn, argtypes=argtypes, restype=restype)


def _buffer_to_bytes(buffer, *, free_fn: Callable | None) -> bytes:
    import ctypes

    if buffer is None or not getattr(buffer, "data", None) or buffer.len == 0:
        return b""
    data = ctypes.string_at(buffer.data, buffer.len)
    if free_fn is not None:
        free_fn(buffer)
    return data


def _load_exec_library() -> object | None:
    global _EXEC_LIB, _EXEC_LOAD_ATTEMPTED
    if _EXEC_LOAD_ATTEMPTED:
        return _EXEC_LIB
    _EXEC_LOAD_ATTEMPTED = True
    if not native_exec_enabled():
        return None
    path = native_library_path()
    if path is None or not path.exists():
        return None
    try:
        import ctypes

        _EXEC_LIB = ctypes.CDLL(str(path))
    except OSError:
        _EXEC_LIB = None
    return _EXEC_LIB


def native_exec_available() -> bool:
    return _load_exec_library() is not None


def _call_exec(ir_bytes: bytes, config_bytes: bytes | None) -> NativeOutcome:
    if not native_exec_enabled():
        return _outcome(NativeStatus.NOT_IMPLEMENTED)
    lib = _load_exec_library()
    if lib is None:
        return _outcome(NativeStatus.NOT_IMPLEMENTED)
    import ctypes

    Buffer = _buffer_type()
    fn = _get_function(
        lib,
        "n3_exec_ir",
        argtypes=[ctypes.POINTER(Buffer), ctypes.POINTER(Buffer), ctypes.POINTER(Buffer)],
        restype=ctypes.c_int,
    )
    if fn is None:
        return _outcome(NativeStatus.NOT_IMPLEMENTED)
    free_fn = _get_function(lib, "n3_free", argtypes=[ctypes.POINTER(Buffer)], restype=None)
    ir_data = (ctypes.c_ubyte * len(ir_bytes)).from_buffer_copy(ir_bytes)
    ir_buf = Buffer(data=ctypes.cast(ir_data, ctypes.POINTER(ctypes.c_ubyte)), len=len(ir_bytes))
    if config_bytes is None:
        cfg_buf = Buffer(data=None, len=0)
    else:
        cfg_data = (ctypes.c_ubyte * len(config_bytes)).from_buffer_copy(config_bytes)
        cfg_buf = Buffer(data=ctypes.cast(cfg_data, ctypes.POINTER(ctypes.c_ubyte)), len=len(config_bytes))
    out = Buffer()
    try:
        status = status_from_int(fn(ctypes.byref(ir_buf), ctypes.byref(cfg_buf), ctypes.byref(out)))
    except Exception:
        return _outcome(NativeStatus.ERROR)
    payload = _buffer_to_bytes(out, free_fn=free_fn) if status == NativeStatus.OK else b""
    return _outcome(status, payload if payload else None)


def native_exec_ir(ir_bytes: bytes, config_bytes: bytes | None = None) -> NativeOutcome:
    return _call_exec(ir_bytes, config_bytes)


def _reset_exec_state() -> None:
    global _EXEC_LIB, _EXEC_LOAD_ATTEMPTED
    _EXEC_LIB = None
    _EXEC_LOAD_ATTEMPTED = False


__all__ = [
    "NativeOutcome",
    "native_exec_available",
    "native_exec_enabled",
    "native_exec_ir",
]
