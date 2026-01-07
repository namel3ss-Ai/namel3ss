from __future__ import annotations

import pytest

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program, run_flow


def test_let_block_parses_multiline():
    source = """
flow "demo":
  let:
    a is 10
    b is 5
    c is a + b
"""
    program = parse_program(source)
    lets = [stmt for stmt in program.flows[0].body if isinstance(stmt, ast.Let)]
    assert [stmt.name for stmt in lets] == ["a", "b", "c"]


def test_let_block_parses_inline_commas():
    source = """
flow "demo":
  let:
    a is 10, b is 5, c is a + b
"""
    program = parse_program(source)
    lets = [stmt for stmt in program.flows[0].body if isinstance(stmt, ast.Let)]
    assert [stmt.name for stmt in lets] == ["a", "b", "c"]


def test_let_block_rejects_and_separator():
    source = """
flow "demo":
  let:
    a is 10, b is 5 and c is a + b
"""
    with pytest.raises(Namel3ssError) as excinfo:
        parse_program(source)
    assert "comma" in str(excinfo.value).lower()
    assert excinfo.value.line == 5


def test_let_block_requires_indent():
    source = """
flow "demo":
  let:
  return "ok"
"""
    with pytest.raises(Namel3ssError) as excinfo:
        parse_program(source)
    assert "indented" in str(excinfo.value).lower()
    assert excinfo.value.line == 5


def test_let_block_requires_entries():
    source = """
flow "demo":
  let:
"""
    with pytest.raises(Namel3ssError) as excinfo:
        parse_program(source)
    assert "indented" in str(excinfo.value).lower()


def test_let_block_rejects_duplicate_names():
    source = """
flow "demo":
  let:
    a is 1, a is 2
"""
    with pytest.raises(Namel3ssError) as excinfo:
        parse_program(source)
    assert "duplicate" in str(excinfo.value).lower()


def test_let_block_runtime_matches_inline_lets():
    sugar = """
flow "demo":
  let:
    a is 10
    b is 5
    c is a + b
  return c
"""
    expanded = """
flow "demo":
  let a is 10
  let b is 5
  let c is a + b
  return c
"""
    sugar_result = run_flow(sugar)
    expanded_result = run_flow(expanded)
    assert sugar_result.last_value == expanded_result.last_value == 15
    assert sugar_result.state == expanded_result.state
