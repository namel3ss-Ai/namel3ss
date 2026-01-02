from __future__ import annotations

import re
from typing import List

from namel3ss.lang.keywords import is_keyword
from namel3ss.types import normalize_type_name


def migrate_buttons(lines: List[str]) -> List[str]:
    migrated: List[str] = []
    pattern = re.compile(r'(\s*)button\s+"([^"]+)"\s+calls\s+flow\s+"([^"]+)"\s*$', re.IGNORECASE)
    for line in lines:
        m = pattern.match(line)
        if m:
            indent = m.group(1)
            label = m.group(2)
            flow = m.group(3)
            migrated.append(f'{indent}button "{label}":')
            migrated.append(f"{indent}  calls flow \"{flow}\"")
            continue
        migrated.append(line)
    return migrated


def normalize_spacing(line: str) -> str:
    indent_len = len(line) - len(line.lstrip(" "))
    indent = " " * indent_len
    rest = line.strip()
    if rest == "":
        return ""

    # headers with names
    m = re.match(r'^define\s+function\s+"([^"]+)"\s*:?\s*$', rest, re.IGNORECASE)
    if m:
        return f'{indent}define function "{m.group(1)}":'
    m = re.match(r'^(flow|page|record|ai|agent|tool)\s+"([^"]+)"\s*:?\s*$', rest)
    if m:
        return f'{indent}{m.group(1)} "{m.group(2)}":'

    if rest.startswith("button "):
        m = re.match(r'^button\s+"([^"]+)"\s*:$', rest)
        if m:
            return f'{indent}button "{m.group(1)}":'

    # property with "is"
    m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\s+is\s+(.+)$', rest)
    if m:
        rest = f"{m.group(1)} is {m.group(2)}"

    # ask ai pattern
    m = re.match(
        r'^ask\s+ai\s+"([^"]+)"\s+with\s+input\s*:?\s*(.+?)\s+as\s+([A-Za-z_][A-Za-z0-9_]*)$',
        rest,
    )
    if m:
        rest = f'ask ai "{m.group(1)}" with input: {m.group(2)} as {m.group(3)}'

    # calls flow line
    m = re.match(r'^calls\s+flow\s+"([^"]+)"\s*$', rest)
    if m:
        rest = f'calls flow "{m.group(1)}"'

    # record field declarations to canonical "field \"name\" is <type> ..."
    field_pattern = re.compile(
        r'^(?:field\s+"([^"]+)"\s+)?([A-Za-z_][A-Za-z0-9_]*)\s+(?:is\s+)?'
        r'(string|str|int|integer|number|boolean|bool|json|list|map)(\s+.+)?$'
    )
    m = field_pattern.match(rest)
    if m:
        explicit_name = m.group(1)
        name = explicit_name or m.group(2)
        raw_type = m.group(3)
        canonical_type, _ = normalize_type_name(raw_type)
        type_name = canonical_type
        tail = m.group(4) or ""
        rest = f'field "{name}" is {type_name}{tail}'

    rest = re.sub(r'\s+:', ":", rest)
    return f"{indent}{rest}"


def normalize_indentation(lines: List[str]) -> List[str]:
    result: List[str] = []
    indent_stack = [0]
    for line in lines:
        if line.strip() == "":
            result.append("")
            continue
        leading = len(line) - len(line.lstrip(" "))
        if leading > indent_stack[-1]:
            indent_stack.append(leading)
        else:
            while indent_stack and leading < indent_stack[-1]:
                indent_stack.pop()
            if leading != indent_stack[-1]:
                indent_stack.append(leading)
        depth = max(0, len(indent_stack) - 1)
        content = line.lstrip(" ")
        result.append("  " * depth + content)
    return result


def collapse_blank_lines(lines: List[str]) -> List[str]:
    cleaned: List[str] = []
    for line in lines:
        if line.strip() == "":
            if cleaned and cleaned[-1] == "":
                continue
            cleaned.append("")
        else:
            cleaned.append(line)
    # trim leading/trailing blanks
    while cleaned and cleaned[0] == "":
        cleaned.pop(0)
    while cleaned and cleaned[-1] == "":
        cleaned.pop()
    return cleaned


_FIELD_LINE_RE = re.compile(r'^(\s*)field\s+"([^"]+)"\s+is\s+(.+)$')
_RECORD_HEADER_RE = re.compile(r'^\s*record\s+"[^"]+"\s*:$')
_TOOL_HEADER_RE = re.compile(r'^\s*tool\s+"[^"]+"\s*:$')
_FUNCTION_HEADER_RE = re.compile(r'^\s*define\s+function\s+"[^"]+"\s*:$', re.IGNORECASE)
_FIELDS_HEADER_RE = re.compile(r'^\s*fields\s*:$')
_TOOL_SECTION_RE = re.compile(r'^\s*(input|output)\s*:$')
_FUNCTION_SECTION_RE = re.compile(r'^\s*(input|output)\s*:$')
_VALID_FIELD_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_ALLOWED_KEYWORD_FIELD_NAMES = {"title", "text", "form", "table", "button", "page"}


def normalize_record_fields(lines: List[str]) -> List[str]:
    normalized: List[str] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if _RECORD_HEADER_RE.match(line):
            record_indent = _line_indent(line)
            normalized.append(line)
            idx += 1
            block_lines, idx = _collect_block(lines, idx, record_indent)
            normalized.extend(_normalize_record_block(block_lines, record_indent))
            continue
        if _TOOL_HEADER_RE.match(line):
            tool_indent = _line_indent(line)
            normalized.append(line)
            idx += 1
            block_lines, idx = _collect_block(lines, idx, tool_indent)
            normalized.extend(_normalize_tool_block(block_lines, tool_indent))
            continue
        normalized.append(line)
        idx += 1
    return normalized


def normalize_function_fields(lines: List[str]) -> List[str]:
    normalized: List[str] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if _FUNCTION_HEADER_RE.match(line):
            func_indent = _line_indent(line)
            normalized.append(line)
            idx += 1
            block_lines, idx = _collect_block(lines, idx, func_indent)
            normalized.extend(_normalize_function_block(block_lines, func_indent))
            continue
        normalized.append(line)
        idx += 1
    return normalized


def _normalize_function_block(lines: List[str], func_indent: int) -> List[str]:
    normalized: List[str] = []
    idx = 0
    body_indent = func_indent + 2
    while idx < len(lines):
        line = lines[idx]
        if line.strip() == "":
            normalized.append(line)
            idx += 1
            continue
        indent = _line_indent(line)
        if indent == body_indent and _FUNCTION_SECTION_RE.match(line):
            normalized.append(line)
            idx += 1
            block_lines, idx = _collect_block(lines, idx, indent)
            normalized.extend(_normalize_tool_fields(block_lines))
            continue
        normalized.append(line)
        idx += 1
    return normalized


def _normalize_record_block(lines: List[str], record_indent: int) -> List[str]:
    normalized: List[str] = []
    idx = 0
    body_indent = record_indent + 2
    while idx < len(lines):
        line = lines[idx]
        if line.strip() == "":
            normalized.append(line)
            idx += 1
            continue
        indent = _line_indent(line)
        if indent == body_indent and _FIELDS_HEADER_RE.match(line):
            normalized.append(line)
            idx += 1
            block_lines, idx = _collect_block(lines, idx, indent)
            normalized.extend(_normalize_fields_block(block_lines))
            continue
        if indent == body_indent:
            run_start = idx
            run_lines: List[str] = []
            run_names: List[str] = []
            while idx < len(lines):
                next_line = lines[idx]
                if next_line.strip() == "":
                    break
                if _line_indent(next_line) != body_indent:
                    break
                match = _FIELD_LINE_RE.match(next_line)
                if not match:
                    break
                run_lines.append(next_line)
                run_names.append(match.group(2))
                idx += 1
            if run_lines:
                if len(run_lines) >= 3 and all(_is_field_identifier(name) for name in run_names):
                    normalized.append(" " * body_indent + "fields:")
                    for field_line, name in zip(run_lines, run_names):
                        tail = _FIELD_LINE_RE.match(field_line).group(3)
                        normalized.append(" " * (body_indent + 2) + f"{name} is {tail}")
                    continue
                normalized.extend(run_lines)
                continue
            idx = run_start
        normalized.append(line)
        idx += 1
    return normalized


def _normalize_tool_block(lines: List[str], tool_indent: int) -> List[str]:
    normalized: List[str] = []
    idx = 0
    body_indent = tool_indent + 2
    while idx < len(lines):
        line = lines[idx]
        if line.strip() == "":
            normalized.append(line)
            idx += 1
            continue
        indent = _line_indent(line)
        if indent == body_indent and _TOOL_SECTION_RE.match(line):
            normalized.append(line)
            idx += 1
            block_lines, idx = _collect_block(lines, idx, indent)
            normalized.extend(_normalize_tool_fields(block_lines))
            continue
        normalized.append(line)
        idx += 1
    return normalized


def _normalize_fields_block(lines: List[str]) -> List[str]:
    normalized: List[str] = []
    for line in lines:
        match = _FIELD_LINE_RE.match(line)
        if match and _is_field_identifier(match.group(2)):
            indent = match.group(1)
            name = match.group(2)
            tail = match.group(3)
            normalized.append(f"{indent}{name} is {tail}")
        else:
            normalized.append(line)
    return normalized


def _normalize_tool_fields(lines: List[str]) -> List[str]:
    normalized: List[str] = []
    for line in lines:
        match = _FIELD_LINE_RE.match(line)
        if match:
            indent = match.group(1)
            name = match.group(2)
            tail = match.group(3)
            normalized.append(f"{indent}{name} is {tail}")
        else:
            normalized.append(line)
    return normalized


def _is_field_identifier(name: str) -> bool:
    if not _VALID_FIELD_NAME_RE.match(name):
        return False
    if is_keyword(name) and name not in _ALLOWED_KEYWORD_FIELD_NAMES:
        return False
    return True


def _collect_block(lines: List[str], start_idx: int, parent_indent: int) -> tuple[List[str], int]:
    block_lines: List[str] = []
    idx = start_idx
    while idx < len(lines):
        line = lines[idx]
        if line.strip() == "":
            block_lines.append(line)
            idx += 1
            continue
        if _line_indent(line) <= parent_indent:
            break
        block_lines.append(line)
        idx += 1
    return block_lines, idx


def _line_indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))
