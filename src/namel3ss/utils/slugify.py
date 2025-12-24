from __future__ import annotations

import re


_NON_ALNUM = re.compile(r"[^a-zA-Z0-9]+")


def slugify_tool_name(value: str) -> str:
    text = value.strip()
    slug = _NON_ALNUM.sub("_", text).strip("_").lower()
    if not slug:
        slug = "tool"
    if not slug[0].isalpha() and slug[0] != "_":
        slug = f"tool_{slug}"
    return slug


__all__ = ["slugify_tool_name"]
