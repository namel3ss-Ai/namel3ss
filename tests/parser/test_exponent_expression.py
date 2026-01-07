from __future__ import annotations

from namel3ss.ast import nodes as ast
from tests.conftest import parse_program


def _return_expr(source: str) -> ast.Expression:
    program = parse_program(source)
    stmt = program.flows[0].body[0]
    assert isinstance(stmt, ast.Return)
    return stmt.expression


def test_exponent_parses_basic():
    source = """
flow "demo":
  return 2 ** 3
"""
    expr = _return_expr(source)
    assert isinstance(expr, ast.BinaryOp)
    assert expr.op == "**"


def test_exponent_is_right_associative():
    source = """
flow "demo":
  return 2 ** 3 ** 2
"""
    expr = _return_expr(source)
    assert isinstance(expr, ast.BinaryOp)
    assert expr.op == "**"
    assert isinstance(expr.right, ast.BinaryOp)
    assert expr.right.op == "**"


def test_exponent_precedence_over_multiplicative():
    source = """
flow "demo":
  return 2 * 3 ** 2
"""
    expr = _return_expr(source)
    assert isinstance(expr, ast.BinaryOp)
    assert expr.op == "*"
    assert isinstance(expr.right, ast.BinaryOp)
    assert expr.right.op == "**"


def test_exponent_precedence_over_unary_minus():
    source = """
flow "demo":
  return -2 ** 2
"""
    expr = _return_expr(source)
    assert isinstance(expr, ast.UnaryOp)
    assert expr.op == "-"
    assert isinstance(expr.operand, ast.BinaryOp)
    assert expr.operand.op == "**"


def test_exponent_parenthesized_base():
    source = """
flow "demo":
  return (-2) ** 2
"""
    expr = _return_expr(source)
    assert isinstance(expr, ast.BinaryOp)
    assert expr.op == "**"
    assert isinstance(expr.left, ast.UnaryOp)
