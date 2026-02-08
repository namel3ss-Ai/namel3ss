from __future__ import annotations

DEBUG_ONLY_CATEGORY_TRACE = "trace"
DEBUG_ONLY_CATEGORY_RETRIEVAL = "retrieval"
DEBUG_ONLY_CATEGORY_METRICS = "metrics"

DEBUG_ONLY_CATEGORIES: tuple[str, ...] = (
    DEBUG_ONLY_CATEGORY_TRACE,
    DEBUG_ONLY_CATEGORY_RETRIEVAL,
    DEBUG_ONLY_CATEGORY_METRICS,
)
DEBUG_ONLY_CATEGORY_SET: frozenset[str] = frozenset(DEBUG_ONLY_CATEGORIES)


def normalize_debug_only_category(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip().lower()
    if token in DEBUG_ONLY_CATEGORY_SET:
        return token
    return None


def parse_diagnostics_flag(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if not isinstance(value, str):
        return False
    token = value.strip().lower()
    return token in {"1", "true", "yes", "on"}


__all__ = [
    "DEBUG_ONLY_CATEGORIES",
    "DEBUG_ONLY_CATEGORY_SET",
    "DEBUG_ONLY_CATEGORY_METRICS",
    "DEBUG_ONLY_CATEGORY_RETRIEVAL",
    "DEBUG_ONLY_CATEGORY_TRACE",
    "normalize_debug_only_category",
    "parse_diagnostics_flag",
]
