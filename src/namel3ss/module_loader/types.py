from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set

from namel3ss.ast import nodes as ast
from namel3ss.ir import nodes as ir


@dataclass
class ModuleExports:
    by_kind: Dict[str, Set[str]] = field(default_factory=dict)

    def add(self, kind: str, name: str) -> None:
        self.by_kind.setdefault(kind, set()).add(name)

    def has(self, kind: str, name: str) -> bool:
        return name in self.by_kind.get(kind, set())

    def kinds(self) -> Dict[str, List[str]]:
        return {kind: sorted(names) for kind, names in self.by_kind.items()}


@dataclass
class ModuleInfo:
    name: str
    path: Path
    capsule: ast.CapsuleDecl
    uses: List[ast.UseDecl]
    programs: List[ast.Program]
    exports: ModuleExports
    files: List[Path]


@dataclass
class ModuleGraph:
    nodes: List[str]
    edges: List[tuple[str, str]]


@dataclass
class ProjectLoadResult:
    program: ir.Program
    app_path: Path
    sources: Dict[Path, str]
    app_ast: ast.Program
    modules: Dict[str, ModuleInfo]
    graph: ModuleGraph
    public_flows: List[str]
