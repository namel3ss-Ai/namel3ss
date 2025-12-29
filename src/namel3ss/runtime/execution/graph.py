from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Node:
    id: str
    kind: str
    title: str
    details: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "title": self.title,
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    kind: str
    note: str

    def as_dict(self) -> dict:
        return {
            "src": self.src,
            "dst": self.dst,
            "kind": self.kind,
            "note": self.note,
        }


@dataclass
class ExplanationGraph:
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "nodes": [node.as_dict() for node in self.nodes],
            "edges": [edge.as_dict() for edge in self.edges],
            "summary": dict(self.summary),
        }


__all__ = ["Edge", "ExplanationGraph", "Node"]
