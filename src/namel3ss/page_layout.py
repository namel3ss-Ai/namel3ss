from __future__ import annotations

from typing import Any


PAGE_LAYOUT_SLOT_ORDER: tuple[str, ...] = (
    "header",
    "sidebar_left",
    "main",
    "drawer_right",
    "footer",
)
PAGE_LAYOUT_SLOT_SET: frozenset[str] = frozenset(PAGE_LAYOUT_SLOT_ORDER)


def is_page_layout_slot(value: object) -> bool:
    return isinstance(value, str) and value in PAGE_LAYOUT_SLOT_SET


def empty_page_layout_dict() -> dict[str, list]:
    return {slot: [] for slot in PAGE_LAYOUT_SLOT_ORDER}


def normalize_page_layout_dict(layout_payload: Any) -> dict[str, list]:
    layout = empty_page_layout_dict()
    if not isinstance(layout_payload, dict):
        return layout
    for slot in PAGE_LAYOUT_SLOT_ORDER:
        values = layout_payload.get(slot)
        layout[slot] = values if isinstance(values, list) else []
    return layout


def flatten_page_layout_values(layout_payload: Any) -> list:
    flattened: list = []
    layout = normalize_page_layout_dict(layout_payload)
    for slot in PAGE_LAYOUT_SLOT_ORDER:
        flattened.extend(layout[slot])
    return flattened


__all__ = [
    "PAGE_LAYOUT_SLOT_ORDER",
    "PAGE_LAYOUT_SLOT_SET",
    "empty_page_layout_dict",
    "flatten_page_layout_values",
    "is_page_layout_slot",
    "normalize_page_layout_dict",
]
