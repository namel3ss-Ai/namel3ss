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


def test_reduce_expression_parses():
    source = """
flow "demo":
  let total is reduce numbers with acc as s and item as n starting 0:
    s + n
"""
    expr = _let_expr(source)
    assert isinstance(expr, ast.ListReduceExpr)
    assert expr.acc_name == "s"
    assert expr.item_name == "n"


def test_reduce_missing_starting_rejected():
    source = """
flow "demo":
  let total is reduce numbers with acc as s and item as n:
    s + n
"""
    with pytest.raises(Namel3ssError) as excinfo:
        parse_program(source)
    assert "starting" in str(excinfo.value).lower()
    assert excinfo.value.line == 4


def test_reduce_missing_acc_rejected():
    source = """
flow "demo":
  let total is reduce numbers with as s and item as n starting 0:
    s + n
"""
    with pytest.raises(Namel3ssError) as excinfo:
        parse_program(source)
    assert "acc" in str(excinfo.value).lower()
    assert excinfo.value.line == 4


def test_reduce_missing_item_rejected():
    source = """
flow "demo":
  let total is reduce numbers with acc as s and as n starting 0:
    s + n
"""
    with pytest.raises(Namel3ssError) as excinfo:
        parse_program(source)
    assert "item" in str(excinfo.value).lower()
    assert excinfo.value.line == 4


def test_reduce_keyword_binding_rejected():
    source = """
flow "demo":
  let total is reduce numbers with acc as if and item as n starting 0:
    if
"""
    with pytest.raises(Namel3ssError) as excinfo:
        parse_program(source)
    assert "keyword" in str(excinfo.value).lower()
    assert excinfo.value.line == 4


def test_reduce_missing_body_rejected():
    source = """
flow "demo":
  let total is reduce numbers with acc as s and item as n starting 0:
  return true
"""
    with pytest.raises(Namel3ssError) as excinfo:
        parse_program(source)
    assert "indented" in str(excinfo.value).lower()
    assert excinfo.value.line == 5
