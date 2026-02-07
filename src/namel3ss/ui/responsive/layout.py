from __future__ import annotations

from namel3ss.errors.base import Namel3ssError


def normalize_columns(
    spans: list[int] | tuple[int, ...],
    *,
    breakpoint_count: int,
    line: int | None,
    column: int | None,
    context: str,
) -> list[int]:
    values = [int(item) for item in spans]
    if not values:
        raise Namel3ssError(f"{context} columns cannot be empty.", line=line, column=column)
    for value in values:
        if value <= 0:
            raise Namel3ssError(f"{context} columns must be positive integers.", line=line, column=column)
        if value > 12:
            raise Namel3ssError(f"{context} columns cannot exceed 12.", line=line, column=column)
    if breakpoint_count <= 0:
        return [values[0]]
    if len(values) > breakpoint_count:
        raise Namel3ssError(
            f"{context} columns define {len(values)} values but only {breakpoint_count} breakpoints are configured.",
            line=line,
            column=column,
        )
    if len(values) < breakpoint_count:
        values.extend([values[0]] * (breakpoint_count - len(values)))
    return values


def apply_responsive_layout_to_pages(pages: list[dict], *, breakpoint_names: tuple[str, ...]) -> None:
    count = len(breakpoint_names)
    for page in pages:
        if not isinstance(page, dict):
            continue
        elements = page.get("elements")
        if isinstance(elements, list):
            _apply_to_elements(elements, breakpoint_count=count)


def _apply_to_elements(elements: list[dict], *, breakpoint_count: int) -> None:
    for element in elements:
        if not isinstance(element, dict):
            continue
        columns = element.get("columns")
        if _is_span_list(columns):
            if breakpoint_count <= 0:
                normalized = [int(columns[0])]
            else:
                normalized = normalize_columns(
                    [int(item) for item in columns],
                    breakpoint_count=breakpoint_count,
                    line=element.get("line"),
                    column=element.get("column"),
                    context=f"{element.get('type', 'element')}",
                )
            element["columns"] = normalized
        children = element.get("children")
        if isinstance(children, list):
            _apply_to_elements(children, breakpoint_count=breakpoint_count)


def _is_span_list(value: object) -> bool:
    if not isinstance(value, list) or not value:
        return False
    for entry in value:
        if isinstance(entry, bool):
            return False
        if isinstance(entry, int):
            continue
        if isinstance(entry, float) and entry.is_integer():
            continue
        return False
    return True


__all__ = ["apply_responsive_layout_to_pages", "normalize_columns"]
