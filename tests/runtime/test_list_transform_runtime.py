from __future__ import annotations

from decimal import Decimal

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import run_flow


def test_map_preserves_order_and_length() -> None:
    source = """
flow "demo":
  let numbers is list:
    1
    2
    3
  return map numbers with item as n:
    n * 2
"""
    result = run_flow(source)
    assert result.last_value == [Decimal("2"), Decimal("4"), Decimal("6")]


def test_filter_preserves_order() -> None:
    source = """
flow "demo":
  let numbers is list:
    1
    2
    3
    10
  return filter numbers with item as n:
    n is greater than 2
"""
    result = run_flow(source)
    assert result.last_value == [Decimal("3"), Decimal("10")]


def test_map_empty_list_returns_empty_list() -> None:
    source = """
flow "demo":
  return map input.values with item as n:
    n * 2
"""
    result = run_flow(source, input_data={"values": []})
    assert result.last_value == []


def test_filter_empty_list_returns_empty_list() -> None:
    source = """
flow "demo":
  return filter input.values with item as n:
    n is greater than 1
"""
    result = run_flow(source, input_data={"values": []})
    assert result.last_value == []


def test_map_rejects_non_list_input() -> None:
    source = """
flow "demo":
  return map input.values with item as n:
    n
"""
    with pytest.raises(Namel3ssError) as excinfo:
        run_flow(source, input_data={"values": 10})
    details = excinfo.value.details or {}
    assert details.get("cause") == {"error_id": "lists.expected_list", "operation": "map"}


def test_filter_rejects_non_list_input() -> None:
    source = """
flow "demo":
  return filter input.values with item as n:
    n is greater than 1
"""
    with pytest.raises(Namel3ssError) as excinfo:
        run_flow(source, input_data={"values": 10})
    details = excinfo.value.details or {}
    assert details.get("cause") == {"error_id": "lists.expected_list", "operation": "filter"}


def test_filter_rejects_non_boolean_predicate() -> None:
    source = """
flow "demo":
  return filter input.values with item as n:
    n + 1
"""
    with pytest.raises(Namel3ssError) as excinfo:
        run_flow(source, input_data={"values": [1]})
    details = excinfo.value.details or {}
    assert details.get("cause") == {"error_id": "lists.expected_boolean"}


def test_map_scoping_does_not_mutate_outer_value() -> None:
    source = """
flow "demo":
  let n is 100
  let numbers is list:
    1
    2
  let doubled is map numbers with item as n:
    n * 2
  return n
"""
    result = run_flow(source)
    assert result.last_value == Decimal("100")


def test_map_item_name_not_available_after_block() -> None:
    source = """
flow "demo":
  let numbers is list:
    1
  let doubled is map numbers with item as n:
    n * 2
  return n
"""
    with pytest.raises(Namel3ssError) as excinfo:
        run_flow(source)
    assert "unknown variable" in str(excinfo.value).lower()


def test_nested_map_scopes_are_independent() -> None:
    source = """
flow "demo":
  let numbers is list:
    1
    2
  return map numbers with item as n:
    map numbers with item as n:
      n + 1
"""
    result = run_flow(source)
    assert result.last_value == [
        [Decimal("2"), Decimal("3")],
        [Decimal("2"), Decimal("3")],
    ]
