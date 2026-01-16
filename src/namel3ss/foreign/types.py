from __future__ import annotations

import difflib

from namel3ss.lang.types import canonicalize_type_name
from namel3ss.runtime.values.types import type_name_for_value
from namel3ss.utils.numbers import is_number


FOREIGN_BASE_TYPES = ("text", "number", "boolean")
_LIST_PREFIX = "list of "
FOREIGN_ALLOWED_TYPES = tuple(
    list(FOREIGN_BASE_TYPES)
    + [f"{_LIST_PREFIX}{base}" for base in FOREIGN_BASE_TYPES]
)


def normalize_foreign_type(raw: str) -> tuple[str, bool]:
    text = " ".join(str(raw or "").strip().lower().split())
    if text.startswith(_LIST_PREFIX):
        item_raw = text[len(_LIST_PREFIX):].strip()
        item_canonical, was_alias = canonicalize_type_name(item_raw)
        return f"{_LIST_PREFIX}{item_canonical}", was_alias
    canonical, was_alias = canonicalize_type_name(text)
    return canonical, was_alias


def foreign_type_suggestions(raw: str, *, limit: int = 3) -> list[str]:
    normalized = " ".join(str(raw or "").strip().lower().split())
    candidates = sorted(FOREIGN_ALLOWED_TYPES)
    return difflib.get_close_matches(normalized, candidates, n=limit, cutoff=0.6)


def is_foreign_type(type_name: str) -> bool:
    normalized = " ".join(str(type_name or "").strip().lower().split())
    if normalized in FOREIGN_BASE_TYPES:
        return True
    if normalized.startswith(_LIST_PREFIX):
        item = normalized[len(_LIST_PREFIX):].strip()
        return item in FOREIGN_BASE_TYPES
    return False


def foreign_value_type(value: object) -> str:
    if isinstance(value, list):
        if not value:
            return "list"
        item_types = {type_name_for_value(item) for item in value}
        if len(item_types) == 1:
            item_type = next(iter(item_types))
            if item_type in FOREIGN_BASE_TYPES:
                return f"{_LIST_PREFIX}{item_type}"
        return "list"
    return type_name_for_value(value)


def foreign_value_matches(value: object, type_name: str) -> bool:
    normalized = " ".join(str(type_name or "").strip().lower().split())
    if normalized == "text":
        return isinstance(value, str)
    if normalized == "number":
        return is_number(value)
    if normalized == "boolean":
        return isinstance(value, bool)
    if normalized.startswith(_LIST_PREFIX):
        item_type = normalized[len(_LIST_PREFIX):].strip()
        if item_type not in FOREIGN_BASE_TYPES:
            return False
        if not isinstance(value, list):
            return False
        return all(foreign_value_matches(item, item_type) for item in value)
    return False


__all__ = [
    "FOREIGN_ALLOWED_TYPES",
    "FOREIGN_BASE_TYPES",
    "foreign_type_suggestions",
    "foreign_value_matches",
    "foreign_value_type",
    "is_foreign_type",
    "normalize_foreign_type",
]
