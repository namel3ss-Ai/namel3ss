from __future__ import annotations

from tests.conftest import run_flow


def test_or_short_circuit_skips_right_side() -> None:
    source = '''spec is "1.0"

flow "demo":
  return true or 1 / 0
'''
    result = run_flow(source)
    assert result.last_value is True


def test_and_short_circuit_skips_right_side() -> None:
    source = '''spec is "1.0"

flow "demo":
  return false and 1 / 0
'''
    result = run_flow(source)
    assert result.last_value is False
