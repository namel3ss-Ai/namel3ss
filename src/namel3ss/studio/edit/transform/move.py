from __future__ import annotations

from typing import List

from namel3ss.errors.base import Namel3ssError
from namel3ss.studio.edit.selectors import find_element_with_parent


def move_element(source: str, manifest: dict, *, op: str, target_element_id: str, page_name: str) -> str:
    element, page, parent, siblings = find_element_with_parent(manifest, target_element_id)
    if parent and parent.get("type") == "row":
        if any(sib.get("type") != "column" for sib in siblings):
            raise Namel3ssError(
                "Row can only contain columns.",
                line=element.get("line"),
                column=element.get("column"),
                details={
                    "op": op,
                    "page": page_name,
                    "element_id": target_element_id,
                    "expected": "column",
                },
            )
    idx = siblings.index(element)
    if op == "move_up":
        if idx == 0:
            return source
        new_order = siblings[:]
        new_order[idx - 1], new_order[idx] = new_order[idx], new_order[idx - 1]
    elif op == "move_down":
        if idx == len(siblings) - 1:
            return source
        new_order = siblings[:]
        new_order[idx], new_order[idx + 1] = new_order[idx + 1], new_order[idx]
    else:
        raise Namel3ssError(f"Unsupported move op '{op}'")
    lines = source.splitlines()
    sibling_spans = [_block_span(lines, _line_of_element(lines, page_name, sib)) for sib in siblings]
    reordered_lines = []
    consumed = set()
    # build new lines respecting new_order
    for sib in new_order:
        span = sibling_spans[siblings.index(sib)]
        start, end = span
        if any(i in consumed for i in range(start, end + 1)):
            raise Namel3ssError("Overlapping spans during move")
        reordered_lines.extend(lines[start : end + 1])
        consumed.update(range(start, end + 1))
    # rebuild source with reordered block
    block_start = sibling_spans[0][0]
    block_end = sibling_spans[-1][1]
    updated = lines[:block_start] + reordered_lines + lines[block_end + 1 :]
    text = "\n".join(updated)
    if source.endswith("\n"):
        text += "\n"
    return text


def _line_of_element(lines: List[str], page_name: str, element: dict) -> int:
    line = element.get("line")
    if isinstance(line, int) and 1 <= line <= len(lines):
        return line - 1
    # fallback: header match
    header = element.get("element_id") or element.get("type")
    for idx, text in enumerate(lines):
        if header and header in text:
            return idx
    raise Namel3ssError("Could not locate element for move")


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
