from __future__ import annotations

from typing import Mapping, Tuple

LayoutSchema = Mapping[str, Tuple[str, ...]]

LAYOUT_NODE_SCHEMA: dict[str, LayoutSchema] = {
    "layout.stack": {"required": ("id", "children", "direction")},
    "layout.row": {"required": ("id", "children")},
    "layout.col": {"required": ("id", "children")},
    "layout.grid": {"required": ("id", "children", "columns")},
    "layout.sidebar": {"required": ("id", "sidebar", "main")},
    "layout.drawer": {"required": ("id", "title", "children")},
    "layout.sticky": {"required": ("id", "position", "children")},
    "conditional.if": {"required": ("id", "condition", "then_children", "else_children")},
    "theme.settings_page": {"required": ("id", "current", "options", "action_id")},
}

OPTIONAL_NODE_FIELDS: dict[str, tuple[str, ...]] = {
    "layout.stack": ("show_when",),
    "layout.row": ("show_when",),
    "layout.col": ("show_when",),
    "layout.grid": ("show_when",),
    "layout.sidebar": ("show_when",),
    "layout.drawer": ("show_when",),
    "layout.sticky": ("show_when",),
    "conditional.if": ("show_when",),
    "theme.settings_page": ("show_when",),
}


__all__ = ["LAYOUT_NODE_SCHEMA", "OPTIONAL_NODE_FIELDS"]
