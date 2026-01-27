from __future__ import annotations

from dataclasses import dataclass

from namel3ss.ir.model.base import Node


@dataclass
class PolicyRule(Node):
    action: str
    mode: str
    permissions: tuple[str, ...]


@dataclass
class PolicyDecl(Node):
    rules: list[PolicyRule]


__all__ = ["PolicyDecl", "PolicyRule"]
