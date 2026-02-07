from __future__ import annotations

import re
from typing import List


_BRACKET_LIST_KEYS = {"labels", "sources", "capabilities", "packs", "only", "allow override"}

_BRACKET_LINE_RE = re.compile(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*(?:\s+override)?)\s*:\s*\[(.*)\]\s*$")
_RECORD_BRACE_INLINE_RE = re.compile(
    r'^(\s*record\s+"[^"]+"(?:\s+version\s+"[^"]+")?(?:\s+shared)?\s*:)\s*\{(.*)\}\s*$'
)
_SMALL_BRACE_INLINE_RE = re.compile(r"^(\s*)(fields|parameters)\s*:\s*\{(.*)\}\s*$")
_BRACKET_MULTI_OPEN_RE = re.compile(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*(?:\s+override)?)\s*:\s*\[\s*$")
_RECORD_BRACE_MULTI_OPEN_RE = re.compile(
    r'^(\s*record\s+"[^"]+"(?:\s+version\s+"[^"]+")?(?:\s+shared)?\s*:)\s*\{\s*$'
)
_SMALL_BRACE_MULTI_OPEN_RE = re.compile(r"^(\s*)(fields|parameters)\s*:\s*\{\s*$")
_MULTI_CLOSE_RE = re.compile(r"^\s*([\]\}])\s*$")


def normalize_grouping_delimiters(lines: List[str]) -> List[str]:
    lines = _normalize_multiline_groupings(lines)
    lines = _normalize_inline_bracket_lists(lines)
    lines = _normalize_inline_record_braces(lines)
    lines = _normalize_inline_small_braces(lines)
    return lines


def _normalize_multiline_groupings(lines: List[str]) -> List[str]:
    normalized: List[str] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        bracket_match = _BRACKET_MULTI_OPEN_RE.match(line)
        if bracket_match:
            indent, key = bracket_match.groups()
            key_norm = key.strip().lower()
            if key_norm in _BRACKET_LIST_KEYS:
                inner_lines, next_idx, close_symbol = _collect_until_group_close(lines, idx + 1)
                if close_symbol == "]":
                    entries = _parse_multiline_entries(inner_lines)
                    if entries is not None:
                        if not entries:
                            normalized.append(f"{indent}{key.strip()}: []")
                        else:
                            normalized.append(f"{indent}{key.strip()}:")
                            for entry in entries:
                                normalized.append(f"{indent}  {entry}")
                        idx = next_idx
                        continue
        record_match = _RECORD_BRACE_MULTI_OPEN_RE.match(line)
        if record_match:
            header = record_match.group(1)
            inner_lines, next_idx, close_symbol = _collect_until_group_close(lines, idx + 1)
            if close_symbol == "}":
                entries = _parse_multiline_entries(inner_lines)
                if entries is not None:
                    if not entries:
                        normalized.append(f"{header} {{}}")
                    else:
                        indent = " " * _line_indent(header)
                        normalized.append(header)
                        for entry in entries:
                            normalized.append(f"{indent}  {entry}")
                    idx = next_idx
                    continue
        small_match = _SMALL_BRACE_MULTI_OPEN_RE.match(line)
        if small_match:
            indent, key = small_match.groups()
            inner_lines, next_idx, close_symbol = _collect_until_group_close(lines, idx + 1)
            if close_symbol == "}":
                entries = _parse_multiline_entries(inner_lines)
                if entries is not None:
                    if not entries:
                        normalized.append(f"{indent}{key}: {{}}")
                    else:
                        normalized.append(f"{indent}{key}:")
                        for entry in entries:
                            normalized.append(f"{indent}  {entry}")
                    idx = next_idx
                    continue
        normalized.append(line)
        idx += 1
    return normalized


def _normalize_inline_bracket_lists(lines: List[str]) -> List[str]:
    normalized: List[str] = []
    for line in lines:
        match = _BRACKET_LINE_RE.match(line)
        if not match:
            normalized.append(line)
            continue
        indent, key, body = match.groups()
        key_norm = key.strip().lower()
        if key_norm not in _BRACKET_LIST_KEYS:
            normalized.append(line)
            continue
        items = _split_csv_items(body)
        if items is None:
            normalized.append(line)
            continue
        if not items:
            normalized.append(f"{indent}{key.strip()}: []")
            continue
        normalized.append(f"{indent}{key.strip()}:")
        for item in items:
            normalized.append(f"{indent}  {item}")
    return normalized


def _normalize_inline_record_braces(lines: List[str]) -> List[str]:
    normalized: List[str] = []
    for line in lines:
        match = _RECORD_BRACE_INLINE_RE.match(line)
        if not match:
            normalized.append(line)
            continue
        header, body = match.groups()
        entries = _split_csv_items(body)
        if entries is None:
            normalized.append(line)
            continue
        if not entries:
            normalized.append(f"{header} {{}}")
            continue
        indent = " " * _line_indent(header)
        normalized.append(header)
        for entry in entries:
            normalized.append(f"{indent}  {entry}")
    return normalized


def _normalize_inline_small_braces(lines: List[str]) -> List[str]:
    normalized: List[str] = []
    for line in lines:
        match = _SMALL_BRACE_INLINE_RE.match(line)
        if not match:
            normalized.append(line)
            continue
        indent, key, body = match.groups()
        entries = _split_csv_items(body)
        if entries is None:
            normalized.append(line)
            continue
        if not entries:
            normalized.append(f"{indent}{key}: {{}}")
            continue
        normalized.append(f"{indent}{key}:")
        for entry in entries:
            normalized.append(f"{indent}  {entry}")
    return normalized


def _line_indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _collect_until_group_close(lines: List[str], start: int) -> tuple[list[str], int, str | None]:
    inner: list[str] = []
    idx = start
    while idx < len(lines):
        line = lines[idx]
        close_match = _MULTI_CLOSE_RE.match(line)
        if close_match:
            return inner, idx + 1, close_match.group(1)
        inner.append(line)
        idx += 1
    return inner, start, None


def _parse_multiline_entries(lines: list[str]) -> list[str] | None:
    entries: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped == "":
            continue
        if stripped.startswith("#"):
            continue
        if any(symbol in stripped for symbol in ("[", "]", "{", "}")):
            return None
        if stripped.endswith(","):
            stripped = stripped[:-1].rstrip()
        if stripped:
            entries.append(stripped)
    return entries


def _split_csv_items(raw: str) -> list[str] | None:
    text = raw.strip()
    if text == "":
        return []
    items: list[str] = []
    current: list[str] = []
    in_string = False
    for ch in text:
        if ch == '"':
            in_string = not in_string
            current.append(ch)
            continue
        if not in_string and ch in {"[", "]", "{", "}"}:
            return None
        if not in_string and ch == ",":
            item = "".join(current).strip()
            if item:
                items.append(item)
            current = []
            continue
        current.append(ch)
    if in_string:
        return None
    tail = "".join(current).strip()
    if tail:
        items.append(tail)
    return items


__all__ = ["normalize_grouping_delimiters"]
