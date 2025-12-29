from __future__ import annotations

from namel3ss.tools_with.model import ToolsWithPack


def render_with(pack: ToolsWithPack) -> str:
    lines: list[str] = ["tools used"]
    lines.extend(_section("Allowed", _render_allowed(pack.allowed)))
    lines.extend(_section("Blocked", _render_blocked(pack.blocked)))
    lines.extend(_section("Errors", _render_errors(pack.errors)))
    if pack.none_used:
        lines.extend(_section("None used", ["none recorded"]))
    return "\n".join(lines).rstrip()


def _section(title: str, entries: list[str]) -> list[str]:
    lines = ["", title]
    if not entries:
        lines.append("- none recorded")
        return lines
    lines.extend([f"- {entry}" for entry in entries])
    return lines


def _render_allowed(entries: list[dict]) -> list[str]:
    return [_entry_label(entry) for entry in entries]


def _render_blocked(entries: list[dict]) -> list[str]:
    rendered: list[str] = []
    for entry in entries:
        tool = _entry_label(entry)
        reason = entry.get("reason") or "unknown"
        capability = entry.get("capability") or "none"
        rendered.append(f"{tool} (reason: {reason}, capability: {capability})")
    return rendered


def _render_errors(entries: list[dict]) -> list[str]:
    return [_entry_label(entry) for entry in entries]


def _entry_label(entry: dict) -> str:
    tool = str(entry.get("tool") or "tool")
    result = entry.get("result")
    if result:
        return f"{tool} ({result})"
    return tool


__all__ = ["render_with"]
