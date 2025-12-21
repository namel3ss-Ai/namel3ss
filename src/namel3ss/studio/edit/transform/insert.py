from __future__ import annotations

from typing import Dict, List

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.schema import records as schema
from namel3ss.studio.edit.selectors import find_element_with_parent


def insert_element(
    source: str,
    target: dict,
    value: dict,
    program: ir.Program,
    manifest: dict,
) -> str:
    page_name = target.get("page")
    element_id = target.get("element_id")
    position = target.get("position") or "inside_end"
    if not isinstance(page_name, str) or not isinstance(element_id, str):
        raise Namel3ssError("Insert target must include 'page' and 'element_id'")
    element, page, parent, siblings = find_element_with_parent(manifest, element_id)
    container = parent if position.startswith("inside") else parent
    if position.startswith("inside"):
        container_element = element if position == "inside_end" else element
    else:
        container_element = parent
    if container_element is None:
        container_element = {"children": page.get("elements", []), "type": "page"}
    container_children = container_element.get("children", page.get("elements", []))
    if position.startswith("inside") and element.get("type") == "row" and (value.get("type") != "column"):
        raise Namel3ssError(
            "Row can only contain columns.",
            line=element.get("line"),
            column=element.get("column"),
            details={
                "op": "insert",
                "page": page_name,
                "element_id": element_id,
                "expected": "column",
                "got": value.get("type"),
            },
        )
    if position.startswith("inside") and element.get("type") != "row" and value.get("type") == "column":
        raise Namel3ssError(
            "Columns must be inserted inside a row.",
            line=element.get("line"),
            column=element.get("column"),
            details={
                "op": "insert",
                "page": page_name,
                "element_id": element_id,
                "expected": "row",
                "got": "column",
            },
        )

    lines = source.splitlines()
    target_start = _find_line(lines, page_name, element)
    if position.startswith("inside"):
        insert_at = _block_end(lines, target_start)
        indent = _leading_spaces(lines[target_start]) + 2
    else:
        start, end = _block_span(lines, target_start)
        insert_at = end + 1
        indent = _leading_spaces(lines[target_start])
    snippet = _element_to_lines(value, indent, program)
    lines[insert_at:insert_at] = snippet
    updated = "\n".join(lines)
    if source.endswith("\n"):
        updated += "\n"
    return updated


def _find_line(lines: List[str], page_name: str, element: dict) -> int:
    line = element.get("line")
    if isinstance(line, int) and 1 <= line <= len(lines):
        return line - 1
    # fallback: scan page for element_id
    for idx, text in enumerate(lines):
        if element.get("element_id") in text and page_name in text:
            return idx
    raise Namel3ssError("Could not locate element for insert")


def _element_to_lines(spec: dict, indent: int, program: ir.Program) -> List[str]:
    space = " " * indent
    t = spec.get("type")
    if t == "title":
        value = spec.get("value") or "New title"
        return [f'{space}title is "{value}"']
    if t == "text":
        value = spec.get("value") or "New text"
        return [f'{space}text is "{value}"']
    if t == "divider":
        return [f"{space}divider"]
    if t == "image":
        src = spec.get("src") or "https://example.com/image.png"
        return [f'{space}image is "{src}"']
    if t == "button":
        label = spec.get("label") or "Button"
        flow = spec.get("flow")
        if not flow:
            flow = program.flows[0].name if program.flows else "flow"
        return [f'{space}button "{label}":', f'{space}  calls flow "{flow}"']
    if t == "form":
        record = spec.get("record")
        if not record:
            record = program.records[0].name if program.records else None
        if not record:
            raise Namel3ssError("Insert form requires a record")
        return [f'{space}form is "{record}"']
    if t == "table":
        record = spec.get("record")
        if not record:
            record = program.records[0].name if program.records else None
        if not record:
            raise Namel3ssError("Insert table requires a record")
        return [f'{space}table is "{record}"']
    if t == "section":
        label = spec.get("label")
        header = f'{space}section "{label}":' if label else f"{space}section:"
        body = _child_lines(spec.get("children") or [{"type": "text", "value": "New text"}], indent + 2, program)
        return [header] + body
    if t == "card":
        label = spec.get("label")
        header = f'{space}card "{label}":' if label else f"{space}card:"
        body = _child_lines(spec.get("children") or [{"type": "text", "value": "New text"}], indent + 2, program)
        return [header] + body
    if t == "row":
        header = f"{space}row:"
        children = spec.get("children") or [{"type": "column", "children": [{"type": "text", "value": "New text"}]}]
        body = _child_lines(children, indent + 2, program, row_context=True)
        return [header] + body
    if t == "column":
        header = f"{space}column:"
        body = _child_lines(spec.get("children") or [{"type": "text", "value": "New text"}], indent + 2, program)
        return [header] + body
    raise Namel3ssError(f"Unsupported element type '{t}' for insert")


def _child_lines(children: List[dict], indent: int, program: ir.Program, row_context: bool = False) -> List[str]:
    lines: List[str] = []
    for child in children:
        if row_context and child.get("type") != "column":
            raise Namel3ssError("Rows may only contain columns")
        lines.extend(_element_to_lines(child, indent, program))
    return lines


def _leading_spaces(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _block_span(lines: List[str], start_idx: int) -> tuple[int, int]:
    start_indent = _leading_spaces(lines[start_idx])
    end = start_idx
    for idx in range(start_idx + 1, len(lines)):
        line = lines[idx]
        if line.strip() == "":
            end = idx
            continue
        if _leading_spaces(line) <= start_indent:
            break
        end = idx
    return start_idx, end


def _block_end(lines: List[str], start_idx: int) -> int:
    return _block_span(lines, start_idx)[1]
