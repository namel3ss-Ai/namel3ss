from __future__ import annotations

from decimal import Decimal

from tests.conftest import run_flow


def test_calc_block_execution_equivalence() -> None:
    calc_source = """
flow "demo":
  let:
    a is 1
    b is 5
    c is 6
  calc:
    d = b ** 2 - 4 * a * c
    root = (-b + d) / (2 * a)
  return d
"""
    let_source = """
flow "demo":
  let:
    a is 1
    b is 5
    c is 6
  let d is b ** 2 - 4 * a * c
  let root is (-b + d) / (2 * a)
  return d
"""
    calc_result = run_flow(calc_source)
    let_result = run_flow(let_source)
    assert calc_result.last_value == let_result.last_value == Decimal("1")


def test_calc_block_composition_execution_equivalence() -> None:
    calc_source = """
flow "demo":
  let numbers is list:
    1
    2
    3
    10
  calc:
    doubled = map numbers with item as n:
      n * 2
    big = filter doubled with item as x:
      x is greater than 5
    total = reduce big with acc as s and item as v starting 0:
      s + v
    avg = mean(big)
  return map:
    "total" is total
    "avg" is avg
"""
    let_source = """
flow "demo":
  let numbers is list:
    1
    2
    3
    10
  let doubled is map numbers with item as n:
    n * 2
  let big is filter doubled with item as x:
    x is greater than 5
  let total is reduce big with acc as s and item as v starting 0:
    s + v
  let avg is mean(big)
  return map:
    "total" is total
    "avg" is avg
"""
    calc_result = run_flow(calc_source)
    let_result = run_flow(let_source)
    assert calc_result.last_value == let_result.last_value


def test_calc_block_state_targets_apply_in_order() -> None:
    source = """
flow "demo":
  calc:
    state.total = 1
    state.total = state.total + 4
  return state.total
"""
    result = run_flow(source)
    assert result.last_value == Decimal("5")
    assert result.state["total"] == Decimal("5")
