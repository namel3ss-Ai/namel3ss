from __future__ import annotations

import re
from typing import List, Tuple

from namel3ss.errors.base import Namel3ssError


def find_element(manifest: dict, element_id: str) -> Tuple[dict, dict]:
    """Locate an element by element_id in the manifest."""
    for page in manifest.get("pages", []):
        found = _find_in_elements(page.get("elements", []), element_id)
        if found:
            return found, page
    raise Namel3ssError(f"Unknown element id '{element_id}'")


def find_element_with_parent(manifest: dict, element_id: str) -> Tuple[dict, dict, dict | None, List[dict]]:
    """Locate an element and its parent container if present."""
    for page in manifest.get("pages", []):
        found = _find_with_parent(page.get("elements", []), element_id, parent=None)
        if found:
            element, parent = found
            siblings = parent["children"] if parent else page.get("elements", [])
            return element, page, parent, siblings
    raise Namel3ssError(f"Unknown element id '{element_id}'")


def _find_with_parent(elements: list[dict], element_id: str, parent: dict | None) -> Tuple[dict, dict | None] | None:
    for element in elements:
        if element.get("element_id") == element_id:
            return element, parent
        nested = element.get("children") or []
        found = _find_with_parent(nested, element_id, element)
        if found:
            return found
    return None


def _find_in_elements(elements: list[dict], element_id: str) -> dict | None:
    for element in elements:
        if element.get("element_id") == element_id:
            return element
        nested = element.get("children") or []
        found = _find_in_elements(nested, element_id)
        if found:
            return found
    return None


def find_line_number(source: str, page_name: str, element: dict) -> int:
    """Best-effort line lookup for an element."""
    line = element.get("line")
    if isinstance(line, int) and line > 0:
        return line
    element_type = element.get("type")
    index = element.get("index", 0)
    line_from_scan = _scan_page_for_element(source, page_name, element_type, index)
    if line_from_scan is None:
        raise Namel3ssError(f"Could not locate element '{element.get('element_id')}' in source")
    return line_from_scan


def _scan_page_for_element(source: str, page_name: str, element_type: str | None, index: int) -> int | None:
    """Fallback scanner when precise line info is missing."""
    lines = source.splitlines()
    page_header = re.compile(rf"^\s*page\s+\"{re.escape(page_name)}\"\s*:")
    in_page = False
    page_indent = 0
    count = 0
    pattern = _element_pattern(element_type)
    for lineno, line in enumerate(lines, start=1):
        if not in_page:
            if page_header.match(line):
                in_page = True
                page_indent = _leading_spaces(line)
            continue
        # inside page
        if line.strip() == "":
            continue
        indent = _leading_spaces(line)
        if indent <= page_indent:
            # page block ended
            break
        if pattern and pattern.match(line):
            if count == index:
                return lineno
            count += 1
    return None


def _leading_spaces(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _element_pattern(element_type: str | None):
    if element_type == "title":
        return re.compile(r'^\s*title\s+is\s+".*"$')
    if element_type == "text":
        return re.compile(r'^\s*text\s+is\s+".*"$')
    if element_type == "button":
        return re.compile(r'^\s*button\s+".*"\s*:')
    if element_type == "form":
        return re.compile(r'^\s*form\s+is\s+".*"')
    if element_type == "table":
        return re.compile(r'^\s*table\s+is\s+".*"')
    if element_type == "section":
        return re.compile(r'^\s*section(\s+".*")?\s*:\s*$')
    if element_type == "card":
        return re.compile(r'^\s*card(\s+".*")?\s*:\s*$')
    if element_type == "row":
        return re.compile(r'^\s*row\s*:\s*$')
    if element_type == "column":
        return re.compile(r'^\s*column\s*:\s*$')
    if element_type == "divider":
        return re.compile(r'^\s*divider\s*$')
    if element_type == "image":
        return re.compile(r'^\s*image\s+is\s+".*"')
    return None
