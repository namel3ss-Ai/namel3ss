from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


def _parse_toml(text: str, path: Path) -> Dict[str, Any]:
    try:
        import tomllib  # type: ignore
    except Exception:
        return _parse_toml_minimal(text, path)
    try:
        data = tomllib.loads(text)
    except Exception as err:
        raise Namel3ssError(
            build_guidance_message(
                what="namel3ss.toml is not valid TOML.",
                why=f"TOML parsing failed: {err}.",
                fix="Fix the TOML syntax in namel3ss.toml.",
                example='[persistence]\\ntarget = "sqlite"',
            )
        ) from err
    return data if isinstance(data, dict) else {}


def _parse_toml_minimal(text: str, path: Path) -> Dict[str, Any]:
    current = None
    data: Dict[str, Any] = {}
    line_num = 0
    for raw_line in text.splitlines():
        line_num += 1
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            data.setdefault(section, {})
            current = section
            continue
        if current is None:
            continue
        if "=" not in line:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Invalid line in {path.name}.",
                    why="Expected key = value inside a section.",
                    fix="Add a key/value entry under a section header.",
                    example='target = "sqlite"',
                ),
                line=line_num,
                column=1,
            )
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        data[current][key] = _parse_toml_value(value, line_num, path)
    return data


def _parse_toml_value(value: str, line_num: int, path: Path) -> Any:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as err:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unsupported array value in {path.name}.",
                    why=f"Array parsing failed: {err}.",
                    fix="Use a JSON-style array of strings.",
                    example='enabled_packs = ["pack.slug"]',
                ),
                line=line_num,
                column=1,
            ) from err
        if not isinstance(parsed, list) or any(not isinstance(item, str) for item in parsed):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unsupported array value in {path.name}.",
                    why="Only arrays of strings are supported.",
                    fix="Provide a list of quoted strings.",
                    example='enabled_packs = ["pack.slug"]',
                ),
                line=line_num,
                column=1,
            )
        return parsed
    if value.startswith("{") and value.endswith("}"):
        return _parse_inline_table(value, line_num, path)
    raise Namel3ssError(
        build_guidance_message(
            what=f"Unsupported value in {path.name}.",
            why="Only quoted strings, arrays of strings, and inline tables are supported.",
            fix="Wrap values in quotes, use arrays, or use inline tables.",
            example='enabled_packs = ["pack.slug"]',
        ),
        line=line_num,
        column=1,
    )


def _parse_inline_table(value: str, line_num: int, path: Path) -> Dict[str, Any]:
    inner = value[1:-1].strip()
    if not inner:
        return {}
    parts = _split_inline_parts(inner)
    table: Dict[str, Any] = {}
    for part in parts:
        if "=" not in part:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Inline table entry is invalid in {path.name}.",
                    why='Entries must be key = "value" pairs.',
                    fix="Add key/value pairs separated by commas.",
                    example='{ api_key = "token" }',
                ),
                line=line_num,
                column=1,
            )
        key, raw_value = part.split("=", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        table[key] = _parse_toml_value(raw_value, line_num, path)
    return table


def _split_inline_parts(text: str) -> list[str]:
    parts: list[str] = []
    current = []
    in_string = False
    escape = False
    for ch in text:
        if escape:
            current.append(ch)
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            current.append(ch)
            continue
        if ch == '"':
            in_string = not in_string
            current.append(ch)
            continue
        if ch == "," and not in_string:
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []
            continue
        current.append(ch)
    part = "".join(current).strip()
    if part:
        parts.append(part)
    return parts


__all__ = [
    "_parse_toml",
    "_parse_toml_minimal",
    "_parse_toml_value",
    "_parse_inline_table",
    "_split_inline_parts",
]
