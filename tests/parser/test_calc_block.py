from __future__ import annotations

import pytest

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def test_calc_block_parses_multiple_assignments() -> None:
    source = """
flow "demo":
  calc:
    d = b ** 2 - 4 * a * c
    root = b / 2
"""
    program = parse_program(source)
    stmt = program.flows[0].body[0]
    assert isinstance(stmt, ast.Let)
    assert stmt.name == "d"
    stmt2 = program.flows[0].body[1]
    assert isinstance(stmt2, ast.Let)
    assert stmt2.name == "root"


def test_calc_block_accepts_block_expressions() -> None:
    source = """
flow "demo":
  calc:
    doubled = map numbers with item as n:
      n * 2
    big = filter doubled with item as x:
      x is greater than 5
    total = reduce big with acc as s and item as v starting 0:
      s + v
    avg = mean(big)
"""
    program = parse_program(source)
    body = program.flows[0].body
    assert isinstance(body[0], ast.Let)
    assert isinstance(body[0].expression, ast.ListMapExpr)
    assert isinstance(body[1], ast.Let)
    assert isinstance(body[1].expression, ast.ListFilterExpr)
    assert isinstance(body[2], ast.Let)
    assert isinstance(body[2].expression, ast.ListReduceExpr)
    assert isinstance(body[3], ast.Let)
    assert isinstance(body[3].expression, ast.ListOpExpr)
    assert body[3].expression.kind == "mean"


def test_calc_block_allows_state_targets() -> None:
    source = """
flow "demo":
  calc:
    state.total = 1
"""
    program = parse_program(source)
    stmt = program.flows[0].body[0]
    assert isinstance(stmt, ast.Set)
    assert isinstance(stmt.target, ast.StatePath)
    assert stmt.target.path == ["total"]


def test_calc_missing_equals_rejected() -> None:
    source = """
flow "demo":
  calc:
    d b ** 2
"""
    with pytest.raises(Namel3ssError) as excinfo:
        parse_program(source)
    assert "=" in str(excinfo.value)
    assert excinfo.value.line == 5


def test_calc_missing_lhs_rejected() -> None:
    source = """
flow "demo":
  calc:
    = 1
"""
    with pytest.raises(Namel3ssError) as excinfo:
        parse_program(source)
    assert "identifier" in str(excinfo.value).lower()
    assert excinfo.value.line == 5


def test_calc_missing_rhs_rejected() -> None:
    source = """
flow "demo":
  calc:
    d =
"""
    with pytest.raises(Namel3ssError) as excinfo:
        parse_program(source)
    assert "right-hand" in str(excinfo.value).lower()
    assert excinfo.value.line == 5


def test_calc_keyword_lhs_rejected() -> None:
    source = """
flow "demo":
  calc:
    if = 1
"""
    with pytest.raises(Namel3ssError) as excinfo:
        parse_program(source)
    message = str(excinfo.value)
    assert "reserved" in message.lower()
    assert "`if`" in message
    assert excinfo.value.line == 5


def test_calc_duplicate_name_rejected() -> None:
    source = """
flow "demo":
  calc:
    total = 1
    total = 2
"""
    with pytest.raises(Namel3ssError) as excinfo:
        parse_program(source)
    assert "duplicate" in str(excinfo.value).lower()
    assert excinfo.value.line == 6


@pytest.mark.parametrize(
    "source",
    [
        """
flow "demo":
  calc:
    input.value = 1
""",
        """
flow "demo":
  calc:
    foo.bar = 1
""",
        """
flow "demo":
  calc:
    state = 1
""",
        """
flow "demo":
  calc:
    state. = 1
""",
    ],
)
def test_calc_invalid_targets_rejected(source: str) -> None:
    with pytest.raises(Namel3ssError):
        parse_program(source)


def test_equals_outside_calc_is_rejected() -> None:
    source = """
flow "demo":
  total = 1
"""
    with pytest.raises(Namel3ssError) as excinfo:
        parse_program(source)
    assert excinfo.value.line == 4
