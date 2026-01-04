from __future__ import annotations

import json

from namel3ss.ir import nodes as ir


def render_expression(expr: ir.Expression) -> str:
    if isinstance(expr, ir.Literal):
        if isinstance(expr.value, str):
            return json.dumps(expr.value)
        return str(expr.value)
    if isinstance(expr, ir.VarReference):
        return expr.name
    if isinstance(expr, ir.AttrAccess):
        attrs = ".".join(expr.attrs)
        return f"{expr.base}.{attrs}" if attrs else expr.base
    if isinstance(expr, ir.StatePath):
        return "state." + ".".join(expr.path)
    if isinstance(expr, ir.UnaryOp):
        return f"{expr.op} {render_expression(expr.operand)}"
    if isinstance(expr, ir.Comparison):
        left = render_expression(expr.left)
        right = render_expression(expr.right)
        op = {
            "eq": "is",
            "ne": "is not",
            "gt": ">",
            "lt": "<",
            "gte": ">=",
            "lte": "<=",
        }.get(expr.kind, expr.kind)
        return f"{left} {op} {right}"
    if isinstance(expr, ir.BinaryOp):
        left = render_expression(expr.left)
        right = render_expression(expr.right)
        return f"{left} {expr.op} {right}"
    return "<expression>"


__all__ = ["render_expression"]
