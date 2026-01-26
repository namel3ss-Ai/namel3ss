from __future__ import annotations

import pytest

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def _let_expr(source: str) -> ast.Expression:
    program = parse_program(source)
    stmt = program.flows[0].body[0]
    assert isinstance(stmt, ast.Let)
    return stmt.expression


def test_map_expression_parses():
    source = """
flow "demo":
  let doubled is map numbers with item as n:
    n * 2
"""
    expr = _let_expr(source)
    assert isinstance(expr, ast.ListMapExpr)
    assert expr.var_name == "n"


def test_filter_expression_parses():
    source = """
flow "demo":
  let big is filter numbers with item as n:
    n is greater than 10
"""
    expr = _let_expr(source)
    assert isinstance(expr, ast.ListFilterExpr)
    assert expr.var_name == "n"


def test_map_missing_as_rejected():
    source = """
flow "demo":
  let doubled is map numbers with item n:
    n * 2
"""
    with pytest.raises(Namel3ssError) as excinfo:
        parse_program(source)
    assert "as" in str(excinfo.value).lower()
    assert excinfo.value.line == 4


def test_map_missing_var_name_rejected():
    source = """
flow "demo":
  let doubled is map numbers with item as:
    n * 2
"""
    with pytest.raises(Namel3ssError) as excinfo:
        parse_program(source)
    assert "identifier" in str(excinfo.value).lower()
    assert excinfo.value.line == 4


def test_map_missing_body_rejected():
    source = """
flow "demo":
  let doubled is map numbers with item as n:
  return true
"""
    with pytest.raises(Namel3ssError) as excinfo:
        parse_program(source)
    assert "indented" in str(excinfo.value).lower()
    assert excinfo.value.line == 5


def test_map_keyword_var_rejected():
    source = """
flow "demo":
  let doubled is map numbers with item as if:
    if
"""
    with pytest.raises(Namel3ssError) as excinfo:
        parse_program(source)
    message = str(excinfo.value)
    assert "reserved" in message.lower()
    assert "`if`" in message
    assert excinfo.value.line == 4
