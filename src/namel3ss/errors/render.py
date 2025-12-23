from __future__ import annotations

from pathlib import Path
from typing import Optional

from namel3ss.errors.base import Namel3ssError


def format_error(err: Namel3ssError, source: Optional[object] = None) -> str:
    base = str(err)
    if source is None or err.line is None:
        return base

    source_text = None
    file_path = None
    if isinstance(source, dict):
        details = getattr(err, "details", None) or {}
        file_path = details.get("file")
        if file_path:
            if file_path in source:
                source_text = source.get(file_path)
            else:
                for key, val in source.items():
                    if isinstance(key, Path) and key.as_posix() == file_path:
                        source_text = val
                        break
                    if str(key) == file_path:
                        source_text = val
                        break
        if source_text is None:
            source_text = next(iter(source.values()), None)
    elif isinstance(source, str):
        source_text = source

    if not source_text:
        return base

    lines = source_text.splitlines()
    line_index = err.line - 1
    if line_index < 0 or line_index >= len(lines):
        return base

    line_text = lines[line_index]
    column = err.column if err.column is not None else 1
    caret_pos = max(1, min(column, len(line_text) + 1))
    caret_line = " " * (caret_pos - 1) + "^"
    prefix = f"File: {file_path}\n" if file_path else ""
    return f"{prefix}{base}\n{line_text}\n{caret_line}"
