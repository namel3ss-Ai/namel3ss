from __future__ import annotations

from importlib import import_module

_EXPORTS = {
    "NativeOutcome": ("namel3ss.runtime.native.adapter", "NativeOutcome"),
    "NativeStatus": ("namel3ss.runtime.native.status", "NativeStatus"),
    "native_available": ("namel3ss.runtime.native.adapter", "native_available"),
    "native_chunk_plan": ("namel3ss.runtime.native.adapter", "native_chunk_plan"),
    "native_enabled": ("namel3ss.runtime.native.adapter", "native_enabled"),
    "native_hash": ("namel3ss.runtime.native.adapter", "native_hash"),
    "native_info": ("namel3ss.runtime.native.adapter", "native_info"),
    "native_normalize": ("namel3ss.runtime.native.adapter", "native_normalize"),
    "native_scan": ("namel3ss.runtime.native.adapter", "native_scan"),
    "status_to_code": ("namel3ss.runtime.native.status", "status_to_code"),
}


def __getattr__(name: str):
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(name)
    module_name, attr = target
    module = import_module(module_name)
    value = getattr(module, attr)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + list(_EXPORTS.keys()))


__all__ = list(_EXPORTS.keys())
