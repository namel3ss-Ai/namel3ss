from __future__ import annotations

from typing import Optional

from namel3ss.errors.base import Namel3ssError


def format_error(err: Namel3ssError, source: Optional[str] = None) -> str:
    base = str(err)
    if source is None or err.line is None:
        return base

    lines = source.splitlines()
    line_index = err.line - 1
    if line_index < 0 or line_index >= len(lines):
        return base

    line_text = lines[line_index]
    column = err.column if err.column is not None else 1
    caret_pos = max(1, min(column, len(line_text) + 1))
    caret_line = " " * (caret_pos - 1) + "^"
    return f"{base}\n{line_text}\n{caret_line}"
