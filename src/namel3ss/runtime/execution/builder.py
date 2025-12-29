from __future__ import annotations

from .graph import Edge, ExplanationGraph, Node
from .normalize import SKIP_KINDS

DECISION_KINDS = {
    "decision_if",
    "decision_match",
    "decision_repeat",
    "decision_for_each",
    "decision_try",
}


def build_execution_graph(pack: dict) -> ExplanationGraph:
    steps = _steps(pack)
    nodes: list[Node] = []
    edges: list[Edge] = []
    step_order: list[str] = []

    for step in steps:
        step_id = step.get("id") or ""
        step_order.append(step_id)
        nodes.append(
            Node(
                id=step_id,
                kind=str(step.get("kind") or "step"),
                title=str(step.get("what") or ""),
                details=_step_details(step),
            )
        )

    for prev, curr in _pairwise(nodes):
        edges.append(Edge(src=prev.id, dst=curr.id, kind="next", note="next"))

    last_decision_id = None
    for step in steps:
        kind = step.get("kind")
        if kind in DECISION_KINDS:
            last_decision_id = step.get("id")
            continue
        if kind in SKIP_KINDS and last_decision_id and step.get("because"):
            edges.append(
                Edge(
                    src=last_decision_id,
                    dst=step.get("id") or "",
                    kind="because",
                    note=str(step.get("because")),
                )
            )

    summary = {
        "flow_name": pack.get("flow_name"),
        "ok": pack.get("ok"),
        "summary": pack.get("summary"),
        "step_count": len(steps),
        "step_order": step_order,
    }
    return ExplanationGraph(nodes=nodes, edges=edges, summary=summary)


def _steps(pack: dict) -> list[dict]:
    steps = pack.get("execution_steps") or []
    return [step for step in steps if isinstance(step, dict)]


def _step_details(step: dict) -> dict:
    details = {}
    if step.get("because"):
        details["because"] = step.get("because")
    data = step.get("data")
    if isinstance(data, dict) and data:
        details["data"] = data
    if step.get("line") is not None:
        details["line"] = step.get("line")
    if step.get("column") is not None:
        details["column"] = step.get("column")
    return details


def _pairwise(nodes: list[Node]) -> list[tuple[Node, Node]]:
    return list(zip(nodes, nodes[1:]))


__all__ = ["build_execution_graph"]
