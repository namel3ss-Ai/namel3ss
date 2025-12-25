from __future__ import annotations

from pathlib import Path

from namel3ss.config.loader import CONFIG_FILENAME
from namel3ss.config.model import ToolPacksConfig


def read_pack_config(app_root: Path) -> ToolPacksConfig:
    from namel3ss.config.loader import load_config

    config = load_config(root=app_root)
    return config.tool_packs


def write_pack_config(app_root: Path, config: ToolPacksConfig) -> Path:
    path = app_root / CONFIG_FILENAME
    original = path.read_text(encoding="utf-8") if path.exists() else ""
    cleaned = _remove_section(original, "tool_packs")
    cleaned = cleaned.rstrip() + ("\n" if cleaned.strip() else "")
    section = _render_tool_packs_section(config)
    updated = cleaned + section
    path.write_text(updated, encoding="utf-8")
    return path


def _render_tool_packs_section(config: ToolPacksConfig) -> str:
    lines = ["[tool_packs]"]
    if config.enabled_packs:
        lines.append(f"enabled_packs = {_render_array(config.enabled_packs)}")
    if config.disabled_packs:
        lines.append(f"disabled_packs = {_render_array(config.disabled_packs)}")
    if config.pinned_tools:
        lines.append(f"pinned_tools = {_render_inline_table(config.pinned_tools)}")
    return "\n".join(lines) + "\n"


def _render_array(items: list[str]) -> str:
    quoted = ", ".join(_quote(item) for item in sorted(set(items)))
    return f"[{quoted}]"


def _render_inline_table(values: dict[str, str]) -> str:
    pairs = ", ".join(f"{_quote(key)} = {_quote(value)}" for key, value in sorted(values.items()))
    return f"{{ {pairs} }}"


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
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


__all__ = ["read_pack_config", "write_pack_config"]
