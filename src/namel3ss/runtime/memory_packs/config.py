from __future__ import annotations

from pathlib import Path

from namel3ss.config.loader import CONFIG_FILENAME
from namel3ss.config.model import MemoryPacksConfig


def read_memory_pack_config(app_root: Path) -> MemoryPacksConfig:
    from namel3ss.config.loader import load_config

    config = load_config(root=app_root)
    return config.memory_packs


def write_memory_pack_config(app_root: Path, config: MemoryPacksConfig) -> Path:
    path = app_root / CONFIG_FILENAME
    original = path.read_text(encoding="utf-8") if path.exists() else ""
    cleaned = _remove_section(original, "memory_packs")
    cleaned = cleaned.rstrip() + ("\n" if cleaned.strip() else "")
    section = _render_memory_packs_section(config)
    updated = cleaned + section if section else cleaned
    path.write_text(updated, encoding="utf-8")
    return path


def _render_memory_packs_section(config: MemoryPacksConfig) -> str:
    lines = ["[memory_packs]"]
    default_pack = (config.default_pack or "").strip()
    if default_pack:
        lines.append(f"default_pack = {_quote(default_pack)}")
    if config.agent_overrides:
        lines.append(f"agent_overrides = {_render_inline_table(config.agent_overrides)}")
    if len(lines) == 1:
        return ""
    return "\n".join(lines) + "\n"


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


__all__ = ["read_memory_pack_config", "write_memory_pack_config"]
