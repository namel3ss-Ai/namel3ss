from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from namel3ss.runtime.native.loader import load_library, native_available, native_enabled
from namel3ss.runtime.native.status import NativeStatus, status_from_int, status_to_code


@dataclass(frozen=True, slots=True)
class NativeOutcome:
    status: NativeStatus
    payload: bytes | None
    error_code: str | None

    def should_fallback(self) -> bool:
        return self.status != NativeStatus.OK


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


def _chunk_options_type():
    import ctypes

    class _ChunkOptions(ctypes.Structure):
        _fields_ = [
            ("max_chars", ctypes.c_uint32),
            ("overlap", ctypes.c_uint32),
        ]

    return _ChunkOptions


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


def _call_single_out(name: str) -> NativeOutcome:
    if not native_enabled():
        return _outcome(NativeStatus.NOT_IMPLEMENTED)
    lib = load_library()
    if lib is None:
        return _outcome(NativeStatus.NOT_IMPLEMENTED)
    import ctypes

    Buffer = _buffer_type()
    fn = _get_function(lib, name, argtypes=[ctypes.POINTER(Buffer)], restype=ctypes.c_int)
    if fn is None:
        return _outcome(NativeStatus.NOT_IMPLEMENTED)
    free_fn = _get_function(lib, "n3_free", argtypes=[ctypes.POINTER(Buffer)], restype=None)
    out = Buffer()
    try:
        status = status_from_int(fn(ctypes.byref(out)))
    except Exception:
        return _outcome(NativeStatus.ERROR)
    payload = _buffer_to_bytes(out, free_fn=free_fn) if status == NativeStatus.OK else b""
    return _outcome(status, payload if payload else None)


def _call_in_out(name: str, payload: bytes) -> NativeOutcome:
    if not native_enabled():
        return _outcome(NativeStatus.NOT_IMPLEMENTED)
    lib = load_library()
    if lib is None:
        return _outcome(NativeStatus.NOT_IMPLEMENTED)
    import ctypes

    Buffer = _buffer_type()
    fn = _get_function(lib, name, argtypes=[ctypes.POINTER(Buffer), ctypes.POINTER(Buffer)], restype=ctypes.c_int)
    if fn is None:
        return _outcome(NativeStatus.NOT_IMPLEMENTED)
    free_fn = _get_function(lib, "n3_free", argtypes=[ctypes.POINTER(Buffer)], restype=None)
    data = (ctypes.c_ubyte * len(payload)).from_buffer_copy(payload)
    inp = Buffer(data=ctypes.cast(data, ctypes.POINTER(ctypes.c_ubyte)), len=len(payload))
    out = Buffer()
    try:
        status = status_from_int(fn(ctypes.byref(inp), ctypes.byref(out)))
    except Exception:
        return _outcome(NativeStatus.ERROR)
    payload_out = _buffer_to_bytes(out, free_fn=free_fn) if status == NativeStatus.OK else b""
    return _outcome(status, payload_out if payload_out else None)


def _call_in_options_out(name: str, payload: bytes, *, max_chars: int, overlap: int) -> NativeOutcome:
    if not native_enabled():
        return _outcome(NativeStatus.NOT_IMPLEMENTED)
    lib = load_library()
    if lib is None:
        return _outcome(NativeStatus.NOT_IMPLEMENTED)
    import ctypes

    Buffer = _buffer_type()
    Options = _chunk_options_type()
    fn = _get_function(
        lib,
        name,
        argtypes=[ctypes.POINTER(Buffer), ctypes.POINTER(Options), ctypes.POINTER(Buffer)],
        restype=ctypes.c_int,
    )
    if fn is None:
        return _outcome(NativeStatus.NOT_IMPLEMENTED)
    free_fn = _get_function(lib, "n3_free", argtypes=[ctypes.POINTER(Buffer)], restype=None)
    data = (ctypes.c_ubyte * len(payload)).from_buffer_copy(payload)
    inp = Buffer(data=ctypes.cast(data, ctypes.POINTER(ctypes.c_ubyte)), len=len(payload))
    options = Options(max_chars=max(0, int(max_chars)), overlap=max(0, int(overlap)))
    out = Buffer()
    try:
        status = status_from_int(fn(ctypes.byref(inp), ctypes.byref(options), ctypes.byref(out)))
    except Exception:
        return _outcome(NativeStatus.ERROR)
    payload_out = _buffer_to_bytes(out, free_fn=free_fn) if status == NativeStatus.OK else b""
    return _outcome(status, payload_out if payload_out else None)


def native_info() -> NativeOutcome:
    return _call_single_out("n3_native_info")


def native_scan(source: bytes) -> NativeOutcome:
    return _call_in_out("n3_scan", source)


def native_hash(source: bytes) -> NativeOutcome:
    return _call_in_out("n3_hash", source)


def native_normalize(source: bytes) -> NativeOutcome:
    return _call_in_out("n3_normalize", source)


def native_chunk_plan(source: bytes, *, max_chars: int, overlap: int) -> NativeOutcome:
    return _call_in_options_out("n3_chunk_plan", source, max_chars=max_chars, overlap=overlap)


__all__ = [
    "NativeOutcome",
    "native_available",
    "native_enabled",
    "native_chunk_plan",
    "native_hash",
    "native_info",
    "native_normalize",
    "native_scan",
]
