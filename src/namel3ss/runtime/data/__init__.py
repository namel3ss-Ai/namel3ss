from __future__ import annotations

from namel3ss.runtime.data.backend_interface import (
    BackendAdapter,
    BackendDescriptor,
    describe_backend,
    register_backend,
    resolve_backend,
)


__all__ = [
    "BackendAdapter",
    "BackendDescriptor",
    "describe_backend",
    "register_backend",
    "resolve_backend",
]
