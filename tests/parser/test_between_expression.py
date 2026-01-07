from __future__ import annotations

import pytest

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program, run_flow


def _get_if_condition(source: str) -> ast.Expression:
    program = parse_program(source)
    stmt = program.flows[0].body[0]
    assert isinstance(stmt, ast.If)
    return stmt.condition


def test_between_parses_inclusive():
    source = """
flow "demo":
  if value is between min_val and max_val:
    return true
"""
    cond = _get_if_condition(source)
    assert isinstance(cond, ast.BinaryOp)
    assert cond.op == "and"
    assert isinstance(cond.left, ast.Comparison)
    assert cond.left.kind == "gte"
    assert isinstance(cond.right, ast.Comparison)
    assert cond.right.kind == "lte"


def test_strictly_between_parses_exclusive():
    source = """
flow "demo":
  if value is strictly between min_val and max_val:
    return true
"""
    cond = _get_if_condition(source)
    assert isinstance(cond, ast.BinaryOp)
    assert cond.op == "and"
    assert isinstance(cond.left, ast.Comparison)
    assert cond.left.kind == "gt"
    assert isinstance(cond.right, ast.Comparison)
    assert cond.right.kind == "lt"


def test_between_rejects_missing_and():
    source = """
flow "demo":
  if value is between min_val max_val:
    return true
"""
    with pytest.raises(Namel3ssError) as excinfo:
        parse_program(source)
    assert "and" in str(excinfo.value).lower()
    assert excinfo.value.line == 4


def test_between_rejects_missing_lower_bound():
    source = """
flow "demo":
  if value is between and max_val:
    return true
"""
    with pytest.raises(Namel3ssError) as excinfo:
        parse_program(source)
    assert "lower bound" in str(excinfo.value).lower()
    assert excinfo.value.line == 4


def test_between_rejects_missing_upper_bound():
    source = """
flow "demo":
  if value is between min_val and:
    return true
"""
    with pytest.raises(Namel3ssError) as excinfo:
        parse_program(source)
    assert "upper bound" in str(excinfo.value).lower()
    assert excinfo.value.line == 4


def test_between_rejects_wrong_token_sequence():
    source = """
flow "demo":
  if value is between min_val or max_val:
    return true
"""
    with pytest.raises(Namel3ssError) as excinfo:
        parse_program(source)
    assert "and" in str(excinfo.value).lower()
    assert excinfo.value.line == 4


def test_between_precedence_with_and():
    source = """
flow "demo":
  if value is between min_val and max_val and flag is true:
    return true
"""
    cond = _get_if_condition(source)
    assert isinstance(cond, ast.BinaryOp)
    assert cond.op == "and"
    assert isinstance(cond.left, ast.BinaryOp)
    assert isinstance(cond.right, ast.Comparison)
    assert cond.right.kind == "eq"


def test_between_precedence_with_not():
    source = """
flow "demo":
  if not value is between min_val and max_val:
    return true
"""
    cond = _get_if_condition(source)
    assert isinstance(cond, ast.UnaryOp)
    assert cond.op == "not"
    assert isinstance(cond.operand, ast.BinaryOp)


def test_between_execution_equivalence():
    between_source = """
flow "demo":
  let:
    value is 15
    min_val is 10
    max_val is 20
  if value is between min_val and max_val:
    return true
  return false
"""
    expanded_source = """
flow "demo":
  let:
    value is 15
    min_val is 10
    max_val is 20
  if value is at least min_val and value is at most max_val:
    return true
  return false
"""
    between_result = run_flow(between_source)
    expanded_result = run_flow(expanded_source)
    assert between_result.last_value == expanded_result.last_value == True
