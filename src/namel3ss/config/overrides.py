from __future__ import annotations

import json
from pathlib import Path

from namel3ss.config.loader import CONFIG_FILENAME
from namel3ss.runtime.capabilities.validate import normalize_overrides


def write_capability_overrides(app_root: Path, overrides: dict[str, dict[str, object]]) -> Path:
    normalized = _normalize_overrides_map(overrides)
    path = app_root / CONFIG_FILENAME
    original = path.read_text(encoding="utf-8") if path.exists() else ""
    cleaned = _remove_section(original, "capability_overrides")
    cleaned = cleaned.rstrip() + ("\n" if cleaned.strip() else "")
    section = _render_overrides_section(normalized) if normalized else ""
    updated = (cleaned + section).rstrip() + ("\n" if cleaned.strip() or section else "")
    path.write_text(updated, encoding="utf-8")
    return path


def _normalize_overrides_map(overrides: dict[str, dict[str, object]]) -> dict[str, dict[str, object]]:
    normalized: dict[str, dict[str, object]] = {}
    for tool_name, raw in overrides.items():
        if not isinstance(tool_name, str) or not tool_name:
            continue
        compact = _compact_overrides(normalize_overrides(raw or {}, label=f'"{tool_name}"'))
        if compact:
            normalized[tool_name] = compact
    return normalized


def _compact_overrides(overrides: dict[str, object]) -> dict[str, object]:
    compact: dict[str, object] = {}
    for key, value in overrides.items():
        if key == "secrets_allowed":
            if isinstance(value, list) and value:
                compact[key] = list(value)
            continue
        if value is True:
            compact[key] = True
    return compact


def _render_overrides_section(overrides: dict[str, dict[str, object]]) -> str:
    lines = ["[capability_overrides]"]
    for tool_name in sorted(overrides):
        inline = _render_inline_table(overrides[tool_name])
        lines.append(f"{_quote(tool_name)} = {inline}")
    return "\n".join(lines) + "\n"


def _render_inline_table(values: dict[str, object]) -> str:
    parts: list[str] = []
    for key in sorted(values):
        parts.append(f"{key} = {_render_value(values[key])}")
    return "{ " + ", ".join(parts) + " }"


def _render_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return json.dumps(value)
    raise ValueError("Unsupported override value")


def _remove_section(text: str, section: str) -> str:
    lines = text.splitlines()
    keep: list[str] = []
    in_section = False
    target = f"[{section}]"
    for raw in lines:
        stripped = raw.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_section = stripped == target
            if not in_section:
                keep.append(raw)
            continue
        if in_section:
            continue
        keep.append(raw)
    return "\n".join(keep).rstrip()


def _quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', "\\\"")
    return f'"{escaped}"'


__all__ = ["write_capability_overrides"]
