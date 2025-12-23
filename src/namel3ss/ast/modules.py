from __future__ import annotations

from dataclasses import dataclass
from typing import List

from namel3ss.ast.base import Node


@dataclass
class UseDecl(Node):
    module: str
    alias: str


@dataclass
class CapsuleExport(Node):
    kind: str
    name: str


@dataclass
class CapsuleDecl(Node):
    name: str
    exports: List[CapsuleExport]
