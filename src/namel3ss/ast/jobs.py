from __future__ import annotations

from dataclasses import dataclass
from typing import List

from namel3ss.ast.base import Node
from namel3ss.ast.expressions import Expression
from namel3ss.ast.statements import Statement


@dataclass
class JobDecl(Node):
    name: str
    body: List[Statement]
    when: Expression | None = None
