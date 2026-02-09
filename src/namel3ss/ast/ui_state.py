from __future__ import annotations

from dataclasses import dataclass

from namel3ss.ast.base import Node


@dataclass
class UIStateField(Node):
    key: str
    type_name: str
    raw_type_name: str | None = None


@dataclass
class UIStateDecl(Node):
    ephemeral: list[UIStateField]
    session: list[UIStateField]
    persistent: list[UIStateField]


__all__ = ["UIStateDecl", "UIStateField"]
