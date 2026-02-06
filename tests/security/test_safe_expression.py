from __future__ import annotations

from decimal import Decimal

import pytest

from namel3ss.ir import nodes as ir
from namel3ss.runtime.safe_expression import (
    SafeExpression,
    UnsupportedSafeExpressionError,
    evaluate_safe_expression,
    parse_safe_expression,
)


def test_parse_safe_expression_literal() -> None:
    parsed = parse_safe_expression(ir.Literal(None, None, "hello"))
    assert parsed == SafeExpression(kind="literal", value="hello")


def test_evaluate_safe_expression_unary_number() -> None:
    value = evaluate_safe_expression(ir.UnaryOp(None, None, "-", ir.Literal(None, None, 5)))
    assert value == Decimal("-5")


def test_evaluate_safe_expression_none() -> None:
    assert evaluate_safe_expression(None) is None


def test_parse_safe_expression_rejects_non_literal_expression() -> None:
    expr = ir.BinaryOp(None, None, "+", ir.Literal(None, None, 1), ir.Literal(None, None, 2))
    with pytest.raises(UnsupportedSafeExpressionError) as err:
        parse_safe_expression(expr)
    assert str(err.value) == "Only literal expressions and unary +/- numeric literals are allowed in this context."
