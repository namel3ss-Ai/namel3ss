from __future__ import annotations

from namel3ss.ir import nodes as ir


def summarize_pages(program: ir.Program) -> list[str]:
    return sorted(page.name for page in program.pages)


def summarize_flows(program: ir.Program) -> list[str]:
    return sorted(flow.name for flow in program.flows)


def summarize_records(program: ir.Program) -> list[str]:
    return sorted(record.name for record in program.records)


def summarize_graph(graph) -> list[str]:
    edges_by_src: dict[str, list[str]] = {}
    for src, dst in getattr(graph, "edges", []):
        edges_by_src.setdefault(src, []).append(dst)
    lines: list[str] = []
    for node in sorted(getattr(graph, "nodes", [])):
        deps = sorted(edges_by_src.get(node, []))
        if deps:
            lines.append(f"{node} -> {', '.join(deps)}")
        else:
            lines.append(node)
    return lines


__all__ = ["summarize_flows", "summarize_graph", "summarize_pages", "summarize_records"]
