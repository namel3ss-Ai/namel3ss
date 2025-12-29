from __future__ import annotations

from .graph import ExplanationGraph, Node
from .normalize import SKIP_KINDS, normalize_graph, stable_bullets, stable_truncate


def render_how(graph: ExplanationGraph) -> str:
    normalized = normalize_graph(graph)
    summary = normalized.summary or {}
    nodes_by_id = {node.id: node for node in normalized.nodes}
    order = _step_order(summary, nodes_by_id)
    ordered_nodes = [nodes_by_id[step_id] for step_id in order if step_id in nodes_by_id]

    lines: list[str] = []
    lines.append("How the flow ran")
    lines.extend(stable_bullets(_how_lines(ordered_nodes, summary)))
    lines.append("")
    lines.append("What did not happen")
    lines.extend(stable_bullets(_skipped_lines(ordered_nodes)))
    return "\n".join(lines).rstrip()


def _how_lines(nodes: list[Node], summary: dict) -> list[str]:
    lines: list[str] = []
    summary_line = _summary_line(summary)
    if summary_line:
        lines.append(summary_line)
    for node in nodes:
        if node.kind in SKIP_KINDS:
            continue
        line = _line_for_node(node)
        if line:
            lines.append(line)
    if not lines:
        lines.append("No execution steps were recorded for this run.")
    return lines


def _skipped_lines(nodes: list[Node]) -> list[str]:
    lines: list[str] = []
    for node in nodes:
        if node.kind not in SKIP_KINDS:
            continue
        line = _line_for_node(node)
        if line:
            lines.append(line)
    if not lines:
        lines.append("No skipped steps were recorded for this run.")
    return lines


def _summary_line(summary: dict) -> str:
    summary_text = summary.get("summary")
    if summary_text:
        return str(summary_text)
    flow_name = summary.get("flow_name") or "flow"
    step_count = summary.get("step_count") or 0
    ok = summary.get("ok")
    if ok is False:
        return f"Flow \"{flow_name}\" failed with {step_count} steps."
    return f"Flow \"{flow_name}\" ran with {step_count} steps."


def _line_for_node(node: Node) -> str:
    title = str(node.title).strip()
    if not title:
        return ""
    details = node.details if isinstance(node.details, dict) else {}
    because = details.get("because")
    line = title
    if because:
        line = f"{title} because {because}."
    else:
        line = _ensure_period(title)
    return stable_truncate(line)


def _ensure_period(text: str) -> str:
    if text.endswith("."):
        return text
    return f"{text}."


def _step_order(summary: dict, nodes_by_id: dict[str, Node]) -> list[str]:
    order = summary.get("step_order")
    if isinstance(order, list) and order:
        return [str(step_id) for step_id in order]
    return sorted(nodes_by_id.keys())


__all__ = ["render_how"]
