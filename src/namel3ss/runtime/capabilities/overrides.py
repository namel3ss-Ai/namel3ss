from __future__ import annotations


def unsafe_override_enabled(overrides: object) -> bool:
    if not isinstance(overrides, dict):
        return False
    return overrides.get("allow_unsafe_execution") is True


__all__ = ["unsafe_override_enabled"]
