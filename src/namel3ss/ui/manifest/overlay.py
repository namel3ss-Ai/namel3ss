from __future__ import annotations


def _modal_id(page_slug: str, label: str) -> str:
    return f"page.{page_slug}.modal.{_slugify(label)}"


def _drawer_id(page_slug: str, label: str) -> str:
    return f"page.{page_slug}.drawer.{_slugify(label)}"


def _slugify(text: str) -> str:
    import re

    lowered = text.lower()
    normalized = re.sub(r"[\s_-]+", "_", lowered)
    cleaned = re.sub(r"[^a-z0-9_]", "", normalized)
    collapsed = re.sub(r"_+", "_", cleaned).strip("_")
    return collapsed


__all__ = ["_modal_id", "_drawer_id"]
