from __future__ import annotations

from namel3ss.module_loader import load_project


def run_graph(path: str, *, json_mode: bool) -> tuple[dict | None, str | None]:
    project = load_project(path)
    graph = project.graph
    if json_mode:
        return (
            {
                "nodes": graph.nodes,
                "edges": [{"from": src, "to": dst} for src, dst in graph.edges],
            },
            None,
        )
    lines = []
    edges_by_src: dict[str, list[str]] = {}
    for src, dst in graph.edges:
        edges_by_src.setdefault(src, []).append(dst)
    for node in graph.nodes:
        deps = edges_by_src.get(node, [])
        if deps:
            lines.append(f"{node} -> {', '.join(sorted(deps))}")
        else:
            lines.append(node)
    return None, "\n".join(lines)
