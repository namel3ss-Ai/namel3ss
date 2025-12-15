from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Node:
    line: Optional[int]
    column: Optional[int]


@dataclass
class Statement(Node):
    pass


@dataclass
class Expression(Node):
    pass
