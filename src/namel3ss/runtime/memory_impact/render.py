from __future__ import annotations

from dataclasses import replace

from namel3ss.runtime.memory_impact.model import ImpactResult


def render_impact(result: ImpactResult, *, depth_used: int) -> ImpactResult:
    lines: list[str] = []
    lines.append("Impact summary.")
    lines.append(f"Depth used is {int(depth_used)}.")
    lines.append(f"Items affected count is {len(result.items)}.")
    if not result.items:
        lines.append("No items are affected.")
        return replace(result, lines=lines, path_lines=_render_path_lines(result, depth_used=depth_used))

    for item in result.items:
        lines.append("Affected item.")
        lines.append(_line_with_text("Summary is", item.short_text))
        lines.append(f"Space is {item.space}.")
        lines.append(f"Phase is {item.phase_id}.")
        lines.append(f"Depth is {item.depth}.")
        lines.append(f"Reason is {item.reason}.")
        lines.append(f"id: {item.memory_id}")

    path_lines = _render_path_lines(result, depth_used=depth_used)
    return replace(result, lines=lines, path_lines=path_lines)


def render_change_preview(
    result: ImpactResult,
    *,
    change_kind: str,
    limit: int = 3,
) -> list[str]:
    lines: list[str] = []
    lines.append(f"Change preview for {change_kind}.")
    lines.append(f"Affected items count is {len(result.items)}.")
    if not result.items:
        lines.append("No items are affected.")
        return lines
    for item in result.items[:limit]:
        lines.append("Affected item.")
        lines.append(_line_with_text("Summary is", item.short_text))
        lines.append(f"Reason is {item.reason}.")
        lines.append(f"id: {item.memory_id}")
    if len(result.items) > limit:
        lines.append("More items are affected.")
    return lines


def _render_path_lines(result: ImpactResult, *, depth_used: int) -> list[str]:
    lines: list[str] = []
    lines.append("Impact path.")
    lines.append(f"Depth used is {int(depth_used)}.")
    if not result.items:
        lines.append("No impact path items.")
        return lines
    by_depth: dict[int, list] = {}
    for item in result.items:
        by_depth.setdefault(int(item.depth), []).append(item)
    for depth in sorted(by_depth.keys()):
        lines.append(f"Depth {depth}.")
        for item in by_depth[depth]:
            lines.append("Path item.")
            lines.append(_line_with_text("Summary is", item.short_text))
            lines.append(f"Reason is {item.reason}.")
            lines.append(f"id: {item.memory_id}")
    return lines


def _line_with_text(prefix: str, text: str) -> str:
    cleaned = str(text).strip()
    if cleaned.endswith((".", "!", "?", ";", ":")):
        return f"{prefix} {cleaned}"
    return f"{prefix} {cleaned}."


__all__ = ["render_change_preview", "render_impact"]
