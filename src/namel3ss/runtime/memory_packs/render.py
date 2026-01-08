from __future__ import annotations

from namel3ss.runtime.memory_packs.format import MemoryPack
from namel3ss.runtime.memory_packs.sources import OverrideEntry, SOURCE_DEFAULT, SourceMap


_BRACKET_CHARS = str.maketrans({")": " ", "(": " ", "]": " ", "[": " ", "}": " ", "{": " "})


def active_pack_lines(packs: list[MemoryPack]) -> list[str]:
    if not packs:
        return ["No memory packs loaded."]
    lines = ["Memory packs are active."]
    for pack in packs:
        lines.append(f"Pack id is {_sanitize(pack.pack_id)}.")
    return lines


def pack_order_lines(packs: list[MemoryPack]) -> list[str]:
    return [_sanitize(pack.pack_id) for pack in packs]


def pack_loaded_lines(pack: MemoryPack) -> list[str]:
    lines = [f"Pack name is {_sanitize(pack.pack_name)}.", f"Pack version is {_sanitize(pack.pack_version)}."]
    provides = pack_provides(pack)
    if not provides:
        lines.append("Pack provides no settings.")
        return lines
    for item in provides:
        lines.append(f"Provides {item}.")
    return lines


def pack_provides(pack: MemoryPack) -> list[str]:
    provides: list[str] = []
    if pack.rules is not None:
        provides.append("rules")
    if pack.trust is not None:
        provides.append("trust")
    if pack.agreement is not None:
        provides.append("agreement")
    if pack.budgets is not None:
        provides.append("budgets")
    if pack.lanes is not None:
        provides.append("lane defaults")
    if pack.phase is not None:
        provides.append("phase defaults")
    return provides


def override_summary_lines(overrides: list[OverrideEntry]) -> list[str]:
    if not overrides:
        return ["No local overrides."]
    lines: list[str] = []
    for entry in overrides:
        lines.append(f"Override {_sanitize(entry.field)} from {_sanitize(entry.from_source)} to {_sanitize(entry.to_source)}.")
    return lines


def pack_diff_lines(sources: SourceMap | None) -> list[str]:
    if sources is None:
        return ["No memory pack changes."]
    changes: list[str] = []
    for field, source in sorted(sources.field_sources.items()):
        if source == SOURCE_DEFAULT:
            continue
        changes.append(f"Applied {_sanitize(field)} from {_sanitize(source)}.")
    if not changes:
        return ["No memory pack changes."]
    return ["Memory pack changes."] + changes


def _sanitize(value: object) -> str:
    text = "" if value is None else str(value)
    sanitized = text.translate(_BRACKET_CHARS)
    return " ".join(sanitized.split()).strip()


__all__ = [
    "active_pack_lines",
    "override_summary_lines",
    "pack_diff_lines",
    "pack_loaded_lines",
    "pack_order_lines",
    "pack_provides",
]
