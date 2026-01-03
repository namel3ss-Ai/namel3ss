from __future__ import annotations

from pathlib import Path
from typing import Optional

from namel3ss.errors.base import Namel3ssError
from namel3ss.secrets import collect_secret_values, redact_text


def format_error(err: Namel3ssError, source: Optional[object] = None) -> str:
    base = str(err)
    if source is None or err.line is None:
        return redact_text(base, collect_secret_values())

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
        return redact_text(base, collect_secret_values())

    lines = source_text.splitlines()
    line_index = err.line - 1
    if line_index < 0 or line_index >= len(lines):
        return redact_text(base, collect_secret_values())

    line_text = lines[line_index]
    column = err.column if err.column is not None else 1
    caret_pos = max(1, min(column, len(line_text) + 1))
    caret_line = " " * (caret_pos - 1) + "^"
    prefix = f"File: {file_path}\n" if file_path else ""
    formatted = f"{prefix}{base}\n{line_text}\n{caret_line}"
    return redact_text(formatted, collect_secret_values())


def format_first_run_error(err: Namel3ssError) -> str:
    parts = _parse_guidance(str(err))
    what = parts.get("what") or _fallback_line(str(err))
    why = parts.get("why") or "The app could not complete the request."
    fix = parts.get("fix") or "Review the input and try again."
    next_step = parts.get("example") or "Run the command again after updating the input."
    lines = [
        "Something went wrong",
        "What happened",
        f"- {what}",
        "Why",
        f"- {why}",
        "How to resolve it",
        f"- {fix}",
        "Suggested next step",
        f"- {next_step}",
    ]
    return redact_text("\n".join(lines), collect_secret_values())


def _parse_guidance(text: str) -> dict[str, str]:
    parts: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("What happened:"):
            parts["what"] = stripped.replace("What happened:", "", 1).strip()
        elif stripped.startswith("Why:"):
            parts["why"] = stripped.replace("Why:", "", 1).strip()
        elif stripped.startswith("Fix:"):
            parts["fix"] = stripped.replace("Fix:", "", 1).strip()
        elif stripped.startswith("Example:"):
            parts["example"] = stripped.replace("Example:", "", 1).strip()
    return parts


def _fallback_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return "An unexpected error occurred."


__all__ = ["format_error", "format_first_run_error"]
