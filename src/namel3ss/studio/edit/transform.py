from __future__ import annotations

import re

from namel3ss.errors.base import Namel3ssError


def replace_literal_at_line(source: str, line_no: int, expected: str | None, new_value: str) -> str:
    lines = source.splitlines()
    if line_no < 1 or line_no > len(lines):
        raise Namel3ssError("Element line number out of bounds")
    line_idx = line_no - 1
    line = lines[line_idx]
    matches = list(re.finditer(r'"([^"]*)"', line))
    if not matches:
        raise Namel3ssError("Unable to find a string literal to edit")
    match = _select_match(matches, expected)
    if match is None:
        raise Namel3ssError("Expected string literal not found on target line")
    escaped_value = _escape_string(new_value)
    new_line = line[: match.start()] + f'"{escaped_value}"' + line[match.end() :]
    lines[line_idx] = new_line
    updated = "\n".join(lines)
    if source.endswith("\n"):
        updated += "\n"
    return updated


def _escape_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _select_match(matches: list[re.Match[str]], expected: str | None):
    if expected is None:
        return matches[0]
    for m in matches:
        if m.group(1) == expected:
            return m
    return None
