from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.ir import nodes as ir


def lower_tooltip_item(
    item: ast.TooltipItem,
    *,
    attach_origin,
) -> ir.TooltipItem:
    return attach_origin(
        ir.TooltipItem(
            text=item.text,
            anchor_label=item.anchor_label,
            collapsed_by_default=bool(item.collapsed_by_default),
            line=item.line,
            column=item.column,
        ),
        item,
    )


__all__ = ["lower_tooltip_item"]

