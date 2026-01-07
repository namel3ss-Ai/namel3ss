from __future__ import annotations

import pytest

from namel3ss.ast import nodes as ast
from tests.conftest import parse_program


def _return_expr(source: str) -> ast.Expression:
    program = parse_program(source)
    stmt = program.flows[0].body[0]
    assert isinstance(stmt, ast.Return)
    return stmt.expression


@pytest.mark.parametrize("name", ["sum", "min", "max", "mean", "median"])
def test_list_aggregation_parses(name: str) -> None:
    source = f"""
flow "demo":
  return {name}(numbers)
"""
    expr = _return_expr(source)
    assert isinstance(expr, ast.ListOpExpr)
    assert expr.kind == name
