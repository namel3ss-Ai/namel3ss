from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Set

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.module_loader.types import ModuleGraph


def build_graph(nodes: Iterable[str], edges: Iterable[tuple[str, str]]) -> ModuleGraph:
    node_list = sorted(set(nodes))
    edge_list = sorted(set(edges))
    return ModuleGraph(nodes=node_list, edges=edge_list)


def topo_sort(graph: ModuleGraph) -> List[str]:
    adjacency: Dict[str, List[str]] = defaultdict(list)
    for src, dst in graph.edges:
        adjacency[src].append(dst)
    for key in adjacency:
        adjacency[key] = sorted(adjacency[key])

    visited: Set[str] = set()
    visiting: Set[str] = set()
    order: List[str] = []
    stack: List[str] = []

    def visit(node: str) -> None:
        if node in visited:
            return
        if node in visiting:
            cycle = _cycle_path(stack, node)
            raise Namel3ssError(
                build_guidance_message(
                    what="Circular module import detected.",
                    why=f"Modules form a cycle: {cycle}.",
                    fix="Remove the cycle by extracting shared code into a separate module.",
                    example='use "shared" as shared',
                )
            )
        visiting.add(node)
        stack.append(node)
        for neighbor in adjacency.get(node, []):
            visit(neighbor)
        stack.pop()
        visiting.remove(node)
        visited.add(node)
        order.append(node)

    for node in sorted(graph.nodes):
        visit(node)
    return order


def _cycle_path(stack: List[str], node: str) -> str:
    if node not in stack:
        return node
    idx = stack.index(node)
    cycle_nodes = stack[idx:] + [node]
    return " -> ".join(cycle_nodes)
