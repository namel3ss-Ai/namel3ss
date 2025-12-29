from __future__ import annotations

from typing import Tuple

CANONICAL_TYPES = {"text", "number", "boolean", "json", "list", "map"}

LEGACY_TYPE_ALIASES = {
    "string": "text",
    "str": "text",
    "int": "number",
    "integer": "number",
    "bool": "boolean",
}


def canonicalize_type_name(raw: str) -> Tuple[str, bool]:
    """
    Normalize a raw type name to its canonical form.

    Returns a pair of canonical_type and was_alias.
    """
    if raw in CANONICAL_TYPES:
        return raw, False
    mapped = LEGACY_TYPE_ALIASES.get(raw)
    if mapped:
        return mapped, True
    return raw, False


def normalize_type_name(raw: str) -> Tuple[str, bool]:
    return canonicalize_type_name(raw)


__all__ = [
    "CANONICAL_TYPES",
    "LEGACY_TYPE_ALIASES",
    "canonicalize_type_name",
    "normalize_type_name",
]
