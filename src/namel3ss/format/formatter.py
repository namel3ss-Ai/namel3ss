from __future__ import annotations

from namel3ss.format.rules import collapse_blank_lines, migrate_buttons, normalize_indentation, normalize_spacing


def format_source(source: str) -> str:
    lines = source.splitlines()
    lines = [line.rstrip() for line in lines]
    lines = migrate_buttons(lines)
    lines = [normalize_spacing(line) for line in lines]
    lines = normalize_indentation(lines)
    lines = collapse_blank_lines(lines)
    formatted = "\n".join(lines)
    if formatted and not formatted.endswith("\n"):
        formatted += "\n"
    if not formatted and source.endswith("\n"):
        formatted = "\n"
    return formatted
