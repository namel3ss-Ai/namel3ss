from __future__ import annotations

from typing import Any


def format_plain(value: object) -> str:
    lines: list[str] = []
    _flatten_plain(lines, "", value)
    return "\n".join(lines)


def _flatten_plain(lines: list[str], prefix: str, value: object) -> None:
    if isinstance(value, dict):
        if not value:
            return
        for key in sorted(value.keys(), key=lambda k: str(k)):
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            _flatten_plain(lines, next_prefix, value[key])
        return
    if isinstance(value, (list, tuple)):
        count_key = f"{prefix}.count" if prefix else "count"
        lines.append(f"{count_key}: {len(value)}")
        for index, item in enumerate(value, start=1):
            item_prefix = f"{prefix}.{index}" if prefix else str(index)
            _flatten_plain(lines, item_prefix, item)
        return

    formatted = _format_plain_scalar(value)
    key = prefix or "value"
    lines.append(f"{key}: {formatted}")


def _format_plain_scalar(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return _sanitize_plain_text(str(value))


def _sanitize_plain_text(text: str) -> str:
    return text.replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t")


__all__ = ["format_plain"]
