from __future__ import annotations

from decimal import Decimal

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import run_flow


def test_reduce_preserves_order() -> None:
    source = """
flow "demo":
  let numbers is list:
    1
    2
    3
  return reduce numbers with acc as s and item as n starting 0:
    s + n
"""
    result = run_flow(source)
    assert result.last_value == Decimal("6")


def test_reduce_empty_list_returns_start() -> None:
    source = """
flow "demo":
  return reduce input.values with acc as s and item as n starting 10:
    s + n
"""
    result = run_flow(source, input_data={"values": []})
    assert result.last_value == Decimal("10")


def test_reduce_simple_multiplication() -> None:
    source = """
flow "demo":
  return reduce input.values with acc as s and item as n starting 1:
    s * n
"""
    result = run_flow(source, input_data={"values": [2, 3]})
    assert result.last_value == Decimal("6")


def test_reduce_non_list_input_rejected() -> None:
    source = """
flow "demo":
  return reduce input.values with acc as s and item as n starting 0:
    s + n
"""
    with pytest.raises(Namel3ssError) as excinfo:
        run_flow(source, input_data={"values": 10})
    details = excinfo.value.details or {}
    assert details.get("cause") == {"error_id": "lists.expected_list", "operation": "reduce"}


def test_reduce_body_error_location() -> None:
    source = """
flow "demo":
  return reduce input.values with acc as s and item as n starting 0:
    s + n
"""
    with pytest.raises(Namel3ssError) as excinfo:
        run_flow(source, input_data={"values": ["x"]})
    assert excinfo.value.line == 5
    assert "cannot apply" in str(excinfo.value).lower()


def test_reduce_scoping_outer_values_unchanged() -> None:
    source = """
flow "demo":
  let s is 100
  let numbers is list:
    1
    2
  let total is reduce numbers with acc as s and item as n starting 0:
    s + n
  return s
"""
    result = run_flow(source)
    assert result.last_value == Decimal("100")


def test_reduce_bindings_not_in_outer_scope() -> None:
    source = """
flow "demo":
  let numbers is list:
    1
  let total is reduce numbers with acc as s and item as n starting 0:
    s + n
  return n
"""
    with pytest.raises(Namel3ssError) as excinfo:
        run_flow(source)
    assert "unknown variable" in str(excinfo.value).lower()


def test_reduce_nested_inside_map() -> None:
    source = """
flow "demo":
  return map input.groups with item as group:
    reduce group with acc as s and item as n starting 0:
      s + n
"""
    result = run_flow(source, input_data={"groups": [[1, 2], [3]]})
    assert result.last_value == [Decimal("3"), Decimal("3")]


def test_map_inside_reduce() -> None:
    source = """
flow "demo":
  return reduce input.groups with acc as s and item as g starting 0:
    s + list length of map g with item as n:
      n
"""
    result = run_flow(source, input_data={"groups": [[1, 2], [3]]})
    assert result.last_value == Decimal("3")
