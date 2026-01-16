from __future__ import annotations

from typing import List

from namel3ss.utils.slugify import slugify_text


def _element_id(page_slug: str, kind: str, path: List[int]) -> str:
    suffix = ".".join(str(p) for p in path) if path else "0"
    return f"page.{page_slug}.{kind}.{suffix}"


def _slugify(text: str) -> str:
    return slugify_text(text)


__all__ = ["_element_id", "_slugify"]
