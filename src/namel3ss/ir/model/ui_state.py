from __future__ import annotations

from dataclasses import dataclass

from namel3ss.ir.model.base import Node


UI_STATE_SCOPES = ("ephemeral", "session", "persistent")


@dataclass
class UIStateField(Node):
    key: str
    type_name: str
    default_value: object
    raw_type_name: str | None = None


@dataclass
class UIStateDecl(Node):
    ephemeral: list[UIStateField]
    session: list[UIStateField]
    persistent: list[UIStateField]


def iter_ui_state_fields(decl: UIStateDecl) -> list[tuple[str, UIStateField]]:
    ordered: list[tuple[str, UIStateField]] = []
    for scope in UI_STATE_SCOPES:
        fields = getattr(decl, scope, None) or []
        for field in fields:
            ordered.append((scope, field))
    return ordered


__all__ = ["UI_STATE_SCOPES", "UIStateDecl", "UIStateField", "iter_ui_state_fields"]
