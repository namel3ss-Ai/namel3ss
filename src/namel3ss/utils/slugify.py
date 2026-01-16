from __future__ import annotations

import re


_NON_ALNUM = re.compile(r"[^a-zA-Z0-9]+")
_NON_SLUG = re.compile(r"[^a-z0-9_]")


def slugify_tool_name(value: str) -> str:
    text = value.strip()
    slug = _NON_ALNUM.sub("_", text).strip("_").lower()
    if not slug:
        slug = "tool"
    if not slug[0].isalpha() and slug[0] != "_":
        slug = f"tool_{slug}"
    return slug


def slugify_text(value: str) -> str:
    lowered = value.lower()
    normalized = re.sub(r"[\s_-]+", "_", lowered)
    cleaned = _NON_SLUG.sub("", normalized)
    return re.sub(r"_+", "_", cleaned).strip("_")


__all__ = ["slugify_text", "slugify_tool_name"]
