from __future__ import annotations

from typing import Any, Iterable, Iterator

from namel3ss.page_layout import PAGE_LAYOUT_SLOT_ORDER, normalize_page_layout_dict


def page_has_layout(page: Any) -> bool:
    return isinstance(page, dict) and isinstance(page.get("layout"), dict)


def iter_page_slot_elements(page: Any) -> Iterator[tuple[str, list]]:
    if not isinstance(page, dict):
        return
    layout_payload = page.get("layout")
    if isinstance(layout_payload, dict):
        normalized = normalize_page_layout_dict(layout_payload)
        for slot_name in PAGE_LAYOUT_SLOT_ORDER:
            yield slot_name, normalized[slot_name]
        return
    elements = page.get("elements")
    if isinstance(elements, list):
        yield "elements", elements


def iter_page_element_lists(page: Any) -> Iterator[list]:
    for _, elements in iter_page_slot_elements(page):
        yield elements


def page_root_elements(page: Any) -> list:
    root: list = []
    for elements in iter_page_element_lists(page):
        root.extend(elements)
    return root


def page_diagnostics_elements(page: Any) -> list:
    diagnostics = []
    if not isinstance(page, dict):
        return diagnostics
    blocks = page.get("diagnostics_blocks")
    if isinstance(blocks, list):
        diagnostics.extend(blocks)
    return diagnostics


def walk_elements(elements: Iterable[Any]) -> Iterator[dict]:
    for element in elements:
        if not isinstance(element, dict):
            continue
        yield element
        for children in iter_element_children_lists(element):
            yield from walk_elements(children)


def walk_page_elements(page: Any) -> Iterator[dict]:
    for elements in iter_page_element_lists(page):
        yield from walk_elements(elements)


def iter_element_children_lists(element: dict) -> Iterator[list]:
    if not isinstance(element, dict):
        return
    for key in ("children", "sidebar", "main", "then_children", "else_children"):
        value = element.get(key)
        if isinstance(value, list):
            yield value


__all__ = [
    "iter_element_children_lists",
    "iter_page_element_lists",
    "iter_page_slot_elements",
    "page_has_layout",
    "page_diagnostics_elements",
    "page_root_elements",
    "walk_elements",
    "walk_page_elements",
]
