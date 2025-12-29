from __future__ import annotations

from tests.conftest import run_flow


def test_boolean_operator_precedence() -> None:
    source = '''spec is "1.0"

flow "demo":
  return true or false and false
'''
    result = run_flow(source)
    assert result.last_value is True


def test_not_precedence_over_or() -> None:
    source = '''spec is "1.0"

flow "demo":
  return not true or false
'''
    result = run_flow(source)
    assert result.last_value is False
