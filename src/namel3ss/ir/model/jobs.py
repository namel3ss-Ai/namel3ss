from __future__ import annotations

from dataclasses import dataclass
from typing import List

from namel3ss.ir.model.base import Node, Statement
from namel3ss.ir.model.expressions import Expression


@dataclass
class JobDecl(Node):
    name: str
    body: List[Statement]
    when: Expression | None = None
