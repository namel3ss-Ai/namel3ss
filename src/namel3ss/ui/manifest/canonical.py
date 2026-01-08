from __future__ import annotations

from typing import List


def _element_id(page_slug: str, kind: str, path: List[int]) -> str:
    suffix = ".".join(str(p) for p in path) if path else "0"
    return f"page.{page_slug}.{kind}.{suffix}"


def _slugify(text: str) -> str:
    import re

    lowered = text.lower()
    normalized = re.sub(r"[\s_-]+", "_", lowered)
    cleaned = re.sub(r"[^a-z0-9_]", "", normalized)
    collapsed = re.sub(r"_+", "_", cleaned).strip("_")
    return collapsed


__all__ = ["_element_id", "_slugify"]
