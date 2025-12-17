from __future__ import annotations

import re
from typing import List


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
