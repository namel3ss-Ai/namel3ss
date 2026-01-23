from __future__ import annotations

from typing import Iterable

from namel3ss.ui.consistency_extract import (
    _chart_config,
    _form_config,
    _list_config,
    _table_config,
    _view_config,
)
from namel3ss.ui.consistency_models import ConsistencyLocation, RecordAppearance


_COMPONENT_TYPES = {"table", "list", "form", "chart", "view", "chat"}


def _collect_record_appearances(pages: list[dict]) -> dict[str, list[RecordAppearance]]:
    appearances: dict[str, list[RecordAppearance]] = {}
    for page in pages:
        page_name = str(page.get("name") or page.get("slug") or "page")
        page_slug = str(page.get("slug") or page_name)
        elements = page.get("elements") or []
        record_sources = _collect_page_sources(elements)

        for element in _walk_elements(elements):
            component = _component_type(element)
            record = _record_name(element)
            if not record or not component:
                continue
            location = _element_location(page_name, page_slug, element)
            chart_pairing = None
            if component == "table":
                config = _table_config(element)
            elif component == "list":
                config = _list_config(element)
            elif component == "form":
                config = _form_config(element)
            elif component == "chart":
                chart_pairing = _paired_source_type(record_sources.get(record, set()))
                config = _chart_config(element, record, chart_pairing)
            elif component == "view":
                config = _view_config(element)
            else:
                config = None
            appearances.setdefault(record, []).append(
                RecordAppearance(
                    record=record,
                    component=component,
                    config=config,
                    location=location,
                    page_slug=page_slug,
                    chart_pairing=chart_pairing,
                )
            )
    return appearances


def _collect_page_sources(elements: list[dict]) -> dict[str, set[str]]:
    sources: dict[str, set[str]] = {}
    for element in _walk_elements(elements):
        element_type = element.get("type")
        if element_type not in {"table", "list"}:
            continue
        record = _record_name(element)
        if not record:
            continue
        sources.setdefault(record, set()).add(str(element_type))
    return sources


def _walk_elements(elements: list[dict]) -> Iterable[dict]:
    for element in elements:
        if not isinstance(element, dict):
            continue
        yield element
        children = element.get("children")
        if isinstance(children, list):
            yield from _walk_elements(children)


def _component_type(element: dict) -> str | None:
    element_type = element.get("type")
    if element_type in _COMPONENT_TYPES:
        return str(element_type)
    return None


def _record_name(element: dict) -> str | None:
    record = element.get("record")
    if isinstance(record, str) and record:
        return record
    return None


def _paired_source_type(types: set[str]) -> str | None:
    if "table" in types and "list" in types:
        return "mixed"
    if "table" in types:
        return "table"
    if "list" in types:
        return "list"
    return None


def _element_location(page_name: str, page_slug: str, element: dict) -> ConsistencyLocation:
    return ConsistencyLocation(
        page=page_name,
        page_slug=page_slug,
        path=element.get("element_id"),
        line=element.get("line"),
        column=element.get("column"),
    )


__all__ = [
    "_collect_page_sources",
    "_collect_record_appearances",
    "_component_type",
    "_element_location",
    "_paired_source_type",
    "_record_name",
    "_walk_elements",
]
