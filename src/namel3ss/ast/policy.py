from __future__ import annotations

from dataclasses import dataclass
from typing import List

from namel3ss.ast.base import Node


@dataclass
class PolicyRuleDecl(Node):
    action: str
    mode: str
    permissions: List[str]


@dataclass
class PolicyDecl(Node):
    rules: List[PolicyRuleDecl]


__all__ = ["PolicyDecl", "PolicyRuleDecl"]
