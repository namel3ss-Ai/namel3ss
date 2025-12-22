from __future__ import annotations

from typing import Tuple

CANONICAL_TYPES = {"text", "number", "boolean", "json"}

TYPE_ALIASES = {
    "string": "text",
    "str": "text",
    "int": "number",
    "integer": "number",
    "bool": "boolean",
}


def normalize_type_name(raw: str) -> Tuple[str, bool]:
    """
    Normalize a raw type name to its canonical form.

    Returns (canonical_type, was_alias).
    """
    if raw in CANONICAL_TYPES:
        return raw, False
    mapped = TYPE_ALIASES.get(raw)
    if mapped:
        return mapped, True
    return raw, False
