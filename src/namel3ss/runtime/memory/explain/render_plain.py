from __future__ import annotations

from .graph import ExplanationGraph, Node
from .normalize import normalize_graph, stable_bullets, stable_join


def render_why(graph: ExplanationGraph) -> str:
    normalized = normalize_graph(graph)
    summary = normalized.summary or {}
    lines: list[str] = []
    lines.append("Why memory did what it did")
    lines.append("")
    lines.append("What happened")
    lines.extend(stable_bullets(_what_happened(summary)))
    lines.append("")
    lines.append("Why")
    lines.extend(stable_bullets(_why_lines(normalized, summary)))
    lines.append("")
    lines.append("Why not")
    lines.extend(stable_bullets(_why_not_lines(normalized)))
    return "\n".join(lines).rstrip()


def _what_happened(summary: dict) -> list[str]:
    operation = summary.get("operation") or "recall"
    counts = summary.get("counts") if isinstance(summary.get("counts"), dict) else {}
    total = _total(summary, counts)
    lines: list[str] = []
    if operation == "write":
        lines.append(f"Recorded {total} {_plural(total, 'item')}.")
    else:
        parts = _count_parts(counts)
        details = f": {stable_join(parts)}" if parts else ""
        lines.append(f"Recalled {total} {_plural(total, 'item')}{details}.")
    phase_line = _phase_line(summary)
    if phase_line:
        lines.append(phase_line)
    return lines


def _why_lines(graph: ExplanationGraph, summary: dict) -> list[str]:
    lines: list[str] = []
    spaces = summary.get("spaces_consulted") if isinstance(summary.get("spaces_consulted"), list) else []
    lanes = summary.get("lanes_consulted") if isinstance(summary.get("lanes_consulted"), list) else []
    cache_events = summary.get("cache_events") if isinstance(summary.get("cache_events"), list) else []
    budget_events = summary.get("budget_events") if isinstance(summary.get("budget_events"), list) else []

    if spaces:
        lines.append(f"Used spaces: {stable_join([str(space) for space in spaces])}.")
    if lanes:
        lines.append(f"Used lanes: {stable_join([str(lane) for lane in lanes])}.")
    if cache_events:
        lines.append(f"Cache: {stable_join(_format_labels(cache_events))}.")
    if budget_events:
        lines.append(f"Budget: {stable_join(_format_labels(budget_events))}.")

    for node in _nodes_by_kind(graph, "decision"):
        reason = _reason(node)
        if reason:
            lines.append(f"{node.title} because {reason}.")
        else:
            lines.append(f"{node.title}.")

    if not lines:
        return ["No explicit inclusion reasons were recorded for this run."]
    return lines


def _why_not_lines(graph: ExplanationGraph) -> list[str]:
    skips = _nodes_by_kind(graph, "skip")
    if not skips:
        return ["No explicit skip reasons were recorded for this run."]
    lines: list[str] = []
    for node in skips:
        reason = _reason(node)
        if reason:
            lines.append(f"{node.title} because {reason}.")
        else:
            lines.append(f"{node.title}.")
    return lines


def _nodes_by_kind(graph: ExplanationGraph, kind: str) -> list[Node]:
    return [node for node in graph.nodes if node.kind == kind]


def _reason(node: Node) -> str | None:
    details = node.details if isinstance(node.details, dict) else {}
    reason = details.get("reason")
    return str(reason) if reason else None


def _count_parts(counts: dict) -> list[str]:
    parts: list[str] = []
    for key in ("short_term", "semantic", "profile"):
        value = counts.get(key)
        if isinstance(value, int) and value:
            parts.append(f"{value} {key}")
    return parts


def _total(summary: dict, counts: dict) -> int:
    total = summary.get("total")
    if isinstance(total, int):
        return total
    if counts:
        return sum(value for value in counts.values() if isinstance(value, int))
    return 0


def _phase_line(summary: dict) -> str | None:
    phase_id = summary.get("phase_id")
    phase_mode = summary.get("phase_mode")
    if phase_id and phase_mode:
        return f"Phase: {phase_mode} ({phase_id})."
    if phase_id:
        return f"Phase: {phase_id}."
    if phase_mode:
        return f"Phase: {phase_mode}."
    return None


def _format_labels(labels: list[object]) -> list[str]:
    formatted: list[str] = []
    for label in labels:
        text = str(label)
        formatted.append(text.replace(":", " "))
    return formatted


def _plural(count: int, noun: str) -> str:
    return noun if count == 1 else f"{noun}s"


__all__ = ["render_why"]
