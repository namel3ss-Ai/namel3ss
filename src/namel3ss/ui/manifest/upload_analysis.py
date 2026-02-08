from __future__ import annotations

from dataclasses import fields, is_dataclass

from namel3ss.ir import nodes as ir
from namel3ss.ir.model.expressions import StatePath
from namel3ss.ui.manifest.page_structure import walk_page_elements


def collect_upload_requests(program: ir.Program) -> list[dict]:
    requests: list[dict] = []
    seen: set[str] = set()
    for page in getattr(program, "pages", []) or []:
        for item in _walk_page_items(getattr(page, "items", []) or []):
            if not isinstance(item, ir.UploadItem):
                continue
            name = item.name
            if not isinstance(name, str) or not name.strip():
                continue
            if name in seen:
                continue
            seen.add(name)
            requests.append(
                {
                    "name": name,
                    "accept": list(item.accept or []),
                    "multiple": bool(item.multiple),
                    "required": bool(getattr(item, "required", False)),
                    "label": str(getattr(item, "label", "") or "Upload"),
                    "preview": bool(getattr(item, "preview", False)),
                    "line": getattr(item, "line", None),
                    "column": getattr(item, "column", None),
                }
            )
    return requests


def collect_upload_reference_names(program: ir.Program) -> set[str]:
    names: set[str] = set()
    for value in _walk_tree(program):
        if not isinstance(value, StatePath):
            continue
        path = value.path if isinstance(value.path, list) else []
        if len(path) < 2:
            continue
        if path[0] != "uploads":
            continue
        name = path[1]
        if isinstance(name, str) and name:
            names.add(name)
    return names


def manifest_has_upload_elements(pages: list[dict]) -> bool:
    for page in pages:
        for element in walk_page_elements(page):
            if element.get("type") == "upload":
                return True
    return False


def _walk_page_items(items: list[object]) -> list[object]:
    collected: list[object] = []
    for item in items:
        collected.append(item)
        children = getattr(item, "children", None)
        if isinstance(children, list):
            collected.extend(_walk_page_items(children))
        tabs = getattr(item, "tabs", None)
        if isinstance(tabs, list):
            for tab in tabs:
                tab_children = getattr(tab, "children", None)
                if isinstance(tab_children, list):
                    collected.extend(_walk_page_items(tab_children))
    return collected


def _walk_tree(root: object) -> list[object]:
    stack: list[object] = [root]
    seen: set[int] = set()
    walked: list[object] = []
    while stack:
        current = stack.pop()
        if current is None:
            continue
        if isinstance(current, (str, bytes, int, float, bool)):
            continue
        current_id = id(current)
        if current_id in seen:
            continue
        seen.add(current_id)
        walked.append(current)
        if isinstance(current, dict):
            for value in current.values():
                stack.append(value)
            continue
        if isinstance(current, (list, tuple, set)):
            for value in current:
                stack.append(value)
            continue
        if is_dataclass(current):
            for field in fields(current):
                if field.name in {"line", "column"}:
                    continue
                stack.append(getattr(current, field.name, None))
    return walked


__all__ = [
    "collect_upload_reference_names",
    "collect_upload_requests",
    "manifest_has_upload_elements",
]
