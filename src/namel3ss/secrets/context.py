from __future__ import annotations

from pathlib import Path

_AUDIT_ROOT: Path | None = None
_ENGINE_TARGET: str | None = None


def set_audit_root(path: Path | None) -> None:
    global _AUDIT_ROOT
    _AUDIT_ROOT = path.resolve() if path else None


def get_audit_root(fallback: Path | None = None) -> Path | None:
    if _AUDIT_ROOT is not None:
        return _AUDIT_ROOT
    if fallback is not None:
        return fallback.resolve()
    return None


def set_engine_target(target: str | None) -> None:
    global _ENGINE_TARGET
    _ENGINE_TARGET = target


def get_engine_target(default: str = "local") -> str:
    if _ENGINE_TARGET:
        return _ENGINE_TARGET
    return default


__all__ = ["set_audit_root", "get_audit_root", "set_engine_target", "get_engine_target"]
