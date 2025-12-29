from __future__ import annotations

from .graph import Edge, ExplanationGraph, Node


def normalize_graph(graph: ExplanationGraph) -> ExplanationGraph:
    nodes = sorted(graph.nodes, key=lambda node: (node.kind, node.id))
    edges = sorted(graph.edges, key=lambda edge: (edge.src, edge.dst, edge.kind, edge.note))
    summary = _normalize_dict(graph.summary)
    return ExplanationGraph(nodes=nodes, edges=edges, summary=summary)


def stable_join(items: list[str], sep: str = ", ") -> str:
    return sep.join(items)


def stable_bullets(lines: list[str]) -> list[str]:
    return [line if line.startswith("- ") else f"- {line}" for line in lines]


def stable_truncate(text: str, limit: int = 120) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _normalize_dict(value: object) -> dict:
    if not isinstance(value, dict):
        return {}
    return {key: _normalize_value(value[key]) for key in sorted(value.keys())}


def _normalize_list(value: object) -> list:
    if not isinstance(value, list):
        return []
    return [_normalize_value(entry) for entry in value]


def _normalize_value(value: object) -> object:
    if isinstance(value, dict):
        return _normalize_dict(value)
    if isinstance(value, list):
        return _normalize_list(value)
    return value


__all__ = ["normalize_graph", "stable_bullets", "stable_join", "stable_truncate"]
