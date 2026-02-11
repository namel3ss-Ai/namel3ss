from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.ir.lowering.expressions import _lower_expression


def lower_slider_item(
    item: ast.SliderItem,
    flow_names: set[str],
    page_name: str,
    *,
    attach_origin,
) -> ir.SliderItem:
    if item.flow_name not in flow_names:
        raise Namel3ssError(
            f"Page '{page_name}' slider '{item.label}' references unknown flow '{item.flow_name}'.",
            line=item.line,
            column=item.column,
        )
    lowered_value = _lower_expression(item.value)
    if not isinstance(lowered_value, ir.StatePath):
        raise Namel3ssError("Sliders must bind value to state.<path>.", line=item.line, column=item.column)
    return attach_origin(
        ir.SliderItem(
            label=item.label,
            min_value=float(item.min_value),
            max_value=float(item.max_value),
            step=float(item.step),
            value=lowered_value,
            flow_name=item.flow_name,
            help_text=item.help_text,
            line=item.line,
            column=item.column,
        ),
        item,
    )


__all__ = ["lower_slider_item"]

