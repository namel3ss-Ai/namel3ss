from __future__ import annotations

import json
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
    m = re.match(r'^capabilities\s*:?\s*$', rest, re.IGNORECASE)
    if m:
        return f"{indent}capabilities:"
    m = re.match(r'^(flow|page|record|job|ai|agent|tool)\s+"([^"]+)"\s*:?\s*$', rest)
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
        r'(text|string|str|int|integer|number|boolean|bool|json|list|map)(\s+.+)?$'
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
_QUOTED_FIELD_LINE_RE = re.compile(r'^(\s*)"([^"]+)"\s+is\s+(.+)$')
_BARE_FIELD_LINE_RE = re.compile(r'^(\s*)([A-Za-z_][A-Za-z0-9_]*)\s+is\s+(.+)$')
_SCHEMA_HEADER_RE = re.compile(r'^\s*(record|identity)\s+"[^"]+"\s*:$')
_TOOL_HEADER_RE = re.compile(r'^\s*tool\s+"[^"]+"\s*:$')
_FUNCTION_HEADER_RE = re.compile(r'^\s*define\s+function\s+"[^"]+"\s*:$', re.IGNORECASE)
_CONTRACT_HEADER_RE = re.compile(r'^\s*contract\s+flow\s+"[^"]+"\s*:$')
_CALL_HEADER_RE = re.compile(
    r'^\s*(?:let\s+[A-Za-z_][A-Za-z0-9_]*\s+is\s+)?call\s+(flow|pipeline|tool)\s+"[^"]+"\s*:\s*$'
)
_FIELDS_HEADER_RE = re.compile(r'^\s*fields\s*:$')
_TOOL_SECTION_RE = re.compile(r'^\s*(input|output)\s*:$')
_FUNCTION_SECTION_RE = re.compile(r'^\s*(input|output)\s*:$')
_VALID_FIELD_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_ALLOWED_KEYWORD_FIELD_NAMES = {"title", "text", "form", "table", "button", "page"}
_ALLOWED_FIELD_TYPES = {
    "text",
    "string",
    "str",
    "int",
    "integer",
    "number",
    "boolean",
    "bool",
    "json",
    "list",
    "map",
}


def normalize_record_fields(lines: List[str]) -> List[str]:
    normalized: List[str] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if _SCHEMA_HEADER_RE.match(line):
            record_indent = _line_indent(line)
            normalized.append(line)
            idx += 1
            block_lines, idx = _collect_block(lines, idx, record_indent)
            normalized.extend(_normalize_schema_block(block_lines, record_indent))
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


def normalize_contract_fields(lines: List[str]) -> List[str]:
    normalized: List[str] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if _CONTRACT_HEADER_RE.match(line):
            contract_indent = _line_indent(line)
            normalized.append(line)
            idx += 1
            block_lines, idx = _collect_block(lines, idx, contract_indent)
            normalized.extend(_normalize_contract_block(block_lines, contract_indent))
            continue
        normalized.append(line)
        idx += 1
    return normalized


def normalize_call_fields(lines: List[str]) -> List[str]:
    normalized: List[str] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if _CALL_HEADER_RE.match(line):
            call_indent = _line_indent(line)
            normalized.append(line)
            idx += 1
            block_lines, idx = _collect_block(lines, idx, call_indent)
            normalized.extend(_normalize_call_block(block_lines, call_indent))
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


def _normalize_contract_block(lines: List[str], contract_indent: int) -> List[str]:
    normalized: List[str] = []
    idx = 0
    body_indent = contract_indent + 2
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


def _normalize_call_block(lines: List[str], call_indent: int) -> List[str]:
    normalized: List[str] = []
    idx = 0
    body_indent = call_indent + 2
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


def _normalize_schema_block(lines: List[str], record_indent: int) -> List[str]:
    normalized: List[str] = []
    idx = 0
    body_indent = record_indent + 2
    fields: List[tuple[str, str]] = []
    insert_at: int | None = None
    while idx < len(lines):
        line = lines[idx]
        if line.strip() == "":
            normalized.append(line)
            idx += 1
            continue
        indent = _line_indent(line)
        if indent == body_indent and _FIELDS_HEADER_RE.match(line):
            if insert_at is None:
                insert_at = len(normalized)
            idx += 1
            block_lines, idx = _collect_block(lines, idx, indent)
            fields.extend(_extract_fields(block_lines))
            continue
        if indent == body_indent:
            field_entry = _field_decl_from_line(line, require_type=True)
            if field_entry:
                if insert_at is None:
                    insert_at = len(normalized)
                fields.append(field_entry)
                idx += 1
                continue
        normalized.append(line)
        idx += 1
    if fields:
        if insert_at is None:
            insert_at = len(normalized)
        normalized[insert_at:insert_at] = _format_fields_block(fields, body_indent)
    return normalized


def _extract_fields(lines: List[str]) -> List[tuple[str, str]]:
    fields: List[tuple[str, str]] = []
    for line in lines:
        if line.strip() == "":
            continue
        field_entry = _field_decl_from_line(line, require_type=False)
        if field_entry:
            fields.append(field_entry)
    return fields


def _field_decl_from_line(line: str, *, require_type: bool) -> tuple[str, str] | None:
    match = _FIELD_LINE_RE.match(line)
    if match:
        name = match.group(2)
        tail = match.group(3)
        if require_type and not _tail_has_field_type(tail):
            return None
        return name, tail
    match = _QUOTED_FIELD_LINE_RE.match(line)
    if match:
        name = match.group(2)
        tail = match.group(3)
        if require_type and not _tail_has_field_type(tail):
            return None
        return name, tail
    match = _BARE_FIELD_LINE_RE.match(line)
    if match:
        name = match.group(2)
        tail = match.group(3)
        if require_type and not _tail_has_field_type(tail):
            return None
        return name, tail
    return None


def _tail_has_field_type(tail: str) -> bool:
    head = tail.strip().split()
    if not head:
        return False
    return head[0].lower() in _ALLOWED_FIELD_TYPES


def _format_fields_block(fields: List[tuple[str, str]], body_indent: int) -> List[str]:
    normalized = [" " * body_indent + "fields:"]
    for name, tail in fields:
        field_name = _format_field_name(name)
        normalized.append(" " * (body_indent + 2) + f"{field_name} is {tail}")
    return normalized


def _format_field_name(name: str) -> str:
    if _is_field_identifier(name):
        return name
    return json.dumps(name, ensure_ascii=True)


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
