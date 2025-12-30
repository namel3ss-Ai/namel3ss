from __future__ import annotations

import re


def slug_identifier(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_]", "_", name).lower()
    return slug or "unnamed"


def quote_identifier(name: str) -> str:
    escaped = name.replace('"', '""')
    return f'"{escaped}"'


def escape_like(value: str) -> str:
    # Escape %, _, and backslash for LIKE patterns.
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


__all__ = ["escape_like", "quote_identifier", "slug_identifier"]
