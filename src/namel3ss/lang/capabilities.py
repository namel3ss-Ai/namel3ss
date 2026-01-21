from __future__ import annotations

BUILTIN_CAPABILITIES = ("http", "jobs", "files", "scheduling", "uploads", "secrets")


def normalize_builtin_capability(name: str | None) -> str | None:
    if not isinstance(name, str):
        return None
    value = name.strip().lower()
    if value in BUILTIN_CAPABILITIES:
        return value
    return None


def is_builtin_capability(name: str | None) -> bool:
    return normalize_builtin_capability(name) is not None


__all__ = ["BUILTIN_CAPABILITIES", "is_builtin_capability", "normalize_builtin_capability"]
