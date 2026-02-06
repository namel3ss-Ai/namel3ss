from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from namel3ss.ir import nodes as ir
from namel3ss.utils.numbers import is_number, to_decimal


@dataclass(frozen=True)
class SafeExpression:
    """Canonical parsed form for the small expression subset allowed in guarded paths."""

    kind: str
    value: object


class UnsupportedSafeExpressionError(ValueError):
    """Raised when an expression falls outside the safe, deterministic subset."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def parse_safe_expression(expr: ir.Expression | None) -> SafeExpression:
    if expr is None:
        return SafeExpression(kind="null", value=None)
    if isinstance(expr, ir.Literal):
        return SafeExpression(kind="literal", value=expr.value)
    if isinstance(expr, ir.UnaryOp) and expr.op in {"+", "-"} and isinstance(expr.operand, ir.Literal):
        value = expr.operand.value
        if is_number(value):
            numeric = to_decimal(value)
            normalized: Decimal = numeric if expr.op == "+" else -numeric
            return SafeExpression(kind="unary_number", value=normalized)
    raise UnsupportedSafeExpressionError(
        "Only literal expressions and unary +/- numeric literals are allowed in this context."
    )


def evaluate_safe_expression(expr: ir.Expression | None) -> object:
    return parse_safe_expression(expr).value


__all__ = [
    "SafeExpression",
    "UnsupportedSafeExpressionError",
    "evaluate_safe_expression",
    "parse_safe_expression",
]
