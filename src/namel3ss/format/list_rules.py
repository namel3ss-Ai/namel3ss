from __future__ import annotations

import json
from typing import List

from namel3ss.format.rules import _collect_block, _line_indent


_LIST_INLINE_LIMIT = 80


def normalize_one_of_lists(lines: List[str]) -> List[str]:
    normalized: List[str] = []
    for line in lines:
        normalized.append(_normalize_one_of_line(line))
    return normalized


def normalize_list_literals(lines: List[str]) -> List[str]:
    normalized: List[str] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        header = _find_list_literal_header(line)
        if not header:
            normalized.append(line)
            idx += 1
            continue
        prefix, rest = header
        header_indent = _line_indent(prefix)
        rest_text = rest.strip()
        if rest_text:
            items = _parse_inline_items(rest_text)
            if items is None:
                normalized.append(line)
                idx += 1
                continue
            normalized.extend(_format_list_literal(prefix, items, header_indent))
            idx += 1
            continue
        block_lines, next_idx = _collect_block(lines, idx + 1, header_indent)
        items = _split_list_block_items(block_lines, header_indent + 2)
        normalized.extend(_format_list_literal(prefix, items, header_indent))
        idx = next_idx
    return normalized


def _normalize_one_of_line(line: str) -> str:
    if "one of" not in line or "[" not in line:
        return line
    result = line
    start = 0
    while True:
        found = _find_one_of_bracket(result, start)
        if not found:
            break
        one_of_idx, list_start = found
        list_end = _find_matching_bracket(result, list_start)
        if list_end is None:
            break
        raw_list = result[list_start : list_end + 1]
        try:
            values = json.loads(raw_list)
        except Exception:
            break
        if not isinstance(values, list):
            break
        items = [json.dumps(value, ensure_ascii=True) for value in values]
        replacement = "one of " + ", ".join(items)
        result = result[:one_of_idx] + replacement + result[list_end + 1 :]
        start = one_of_idx + len(replacement)
    return result


def _find_one_of_bracket(line: str, start: int) -> tuple[int, int] | None:
    in_string = False
    i = start
    while i < len(line):
        ch = line[i]
        if ch == '"':
            in_string = not in_string
            i += 1
            continue
        if not in_string and line.startswith("one of", i):
            before = line[i - 1] if i > 0 else ""
            after = line[i + 6] if i + 6 < len(line) else ""
            if before and (before.isalnum() or before == "_"):
                i += 1
                continue
            if after and not after.isspace():
                i += 1
                continue
            j = i + 6
            while j < len(line) and line[j].isspace():
                j += 1
            if j < len(line) and line[j] == "[":
                return i, j
        i += 1
    return None


def _find_matching_bracket(line: str, start: int) -> int | None:
    in_string = False
    i = start + 1
    while i < len(line):
        ch = line[i]
        if ch == '"':
            in_string = not in_string
            i += 1
            continue
        if not in_string and ch == "]":
            return i
        i += 1
    return None


def _find_list_literal_header(line: str) -> tuple[str, str] | None:
    in_string = False
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == '"':
            in_string = not in_string
            i += 1
            continue
        if not in_string and _starts_word(line, i, "list"):
            j = i + 4
            j = _skip_spaces(line, j)
            if _starts_word(line, j, "of"):
                j = _skip_spaces(line, j + 2)
                j = _skip_type_token(line, j)
                j = _skip_spaces(line, j)
            if j < len(line) and line[j] == ":":
                return line[:j].rstrip(), line[j + 1 :]
        i += 1
    return None


def _skip_spaces(line: str, idx: int) -> int:
    while idx < len(line) and line[idx].isspace():
        idx += 1
    return idx


def _skip_type_token(line: str, idx: int) -> int:
    while idx < len(line) and (line[idx].isalnum() or line[idx] in {"_", "."}):
        idx += 1
    return idx


def _starts_word(line: str, idx: int, word: str) -> bool:
    if not line.startswith(word, idx):
        return False
    before = line[idx - 1] if idx > 0 else ""
    after = line[idx + len(word)] if idx + len(word) < len(line) else ""
    if before and (before.isalnum() or before == "_"):
        return False
    if after and (after.isalnum() or after == "_"):
        return False
    return True


def _parse_inline_items(text: str) -> List[str] | None:
    items: List[str] = []
    current: List[str] = []
    in_string = False
    depth_paren = 0
    depth_bracket = 0
    for ch in text:
        if ch == '"':
            in_string = not in_string
            current.append(ch)
            continue
        if not in_string:
            if ch == "(":
                depth_paren += 1
            elif ch == ")":
                depth_paren = max(0, depth_paren - 1)
            elif ch == "[":
                depth_bracket += 1
            elif ch == "]":
                depth_bracket = max(0, depth_bracket - 1)
            if ch == "," and depth_paren == 0 and depth_bracket == 0:
                item = "".join(current).strip()
                if item:
                    items.append(item)
                current = []
                continue
        current.append(ch)
    tail = "".join(current).strip()
    if tail:
        items.append(tail)
    return items


def _split_list_block_items(lines: List[str], item_indent: int) -> List[List[str]]:
    items: List[List[str]] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if line.strip() == "":
            idx += 1
            continue
        if _line_indent(line) < item_indent:
            idx += 1
            continue
        item_lines = [line]
        idx += 1
        while idx < len(lines):
            next_line = lines[idx]
            if next_line.strip() == "":
                idx += 1
                continue
            if _line_indent(next_line) <= item_indent:
                break
            item_lines.append(next_line)
            idx += 1
        items.append(item_lines)
    return items


def _format_list_literal(prefix: str, items: List, header_indent: int) -> List[str]:
    item_texts = _inline_item_texts(items)
    inline = None
    if item_texts is not None:
        inline = prefix + (":" if not item_texts else f": {', '.join(item_texts)}")
        if len(inline) <= _LIST_INLINE_LIMIT:
            return [inline]
    block_lines = [prefix + ":"]
    item_indent = " " * (header_indent + 2)
    if isinstance(items, list) and items and isinstance(items[0], list):
        for item in items:
            if len(item) == 1:
                text = item[0].strip().rstrip(",")
                block_lines.append(f"{item_indent}{text},")
            else:
                block_lines.extend(item)
        return block_lines
    for item in item_texts or []:
        block_lines.append(f"{item_indent}{item.rstrip(',')},")
    return block_lines


def _inline_item_texts(items: List) -> List[str] | None:
    if not items:
        return []
    if isinstance(items[0], list):
        values: List[str] = []
        for item in items:
            if len(item) != 1:
                return None
            text = item[0].strip().rstrip(",")
            if text.endswith(":"):
                return None
            values.append(text)
        return values
    return [item.strip().rstrip(",") for item in items]
