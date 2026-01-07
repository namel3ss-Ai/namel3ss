from __future__ import annotations

from decimal import Decimal

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import run_flow


def _run_aggregate(name: str, values: object) -> object:
    source = f"""
flow "demo":
  return {name}(input.numbers)
"""
    result = run_flow(source, input_data={"numbers": values})
    return result.last_value


@pytest.mark.parametrize(
    "name, values, expected",
    [
        ("sum", [1, 2, 3], Decimal("6")),
        ("min", [3, 1, 2], Decimal("1")),
        ("max", [3, 1, 2], Decimal("3")),
        ("mean", [1, 2, 3], Decimal("2")),
        ("median", [3, 1, 2], Decimal("2")),
    ],
)
def test_list_aggregations_basic(name: str, values: list[int], expected: Decimal) -> None:
    assert _run_aggregate(name, values) == expected


def test_list_median_even_length() -> None:
    assert _run_aggregate("median", [1, 4, 2, 3]) == Decimal("2.5")


def test_list_aggregation_rejects_non_list_input() -> None:
    with pytest.raises(Namel3ssError) as excinfo:
        _run_aggregate("sum", 10)
    details = excinfo.value.details or {}
    assert details.get("cause") == {"error_id": "math.not_list", "operation": "sum"}


def test_list_aggregation_rejects_non_numeric_element() -> None:
    with pytest.raises(Namel3ssError) as excinfo:
        _run_aggregate("mean", [1, "oops"])
    details = excinfo.value.details or {}
    assert details.get("cause") == {"error_id": "math.non_numeric_element", "operation": "mean", "index": 1}


@pytest.mark.parametrize("name", ["sum", "min", "max", "mean", "median"])
def test_list_aggregation_rejects_empty_list(name: str) -> None:
    with pytest.raises(Namel3ssError) as excinfo:
        _run_aggregate(name, [])
    details = excinfo.value.details or {}
    assert details.get("cause") == {"error_id": "math.empty_list", "operation": name}


def test_list_aggregations_return_map_literal() -> None:
    source = """
flow "demo":
  let numbers is list:
    10
    20
    30
  let total is sum(numbers)
  let lo is min(numbers)
  let hi is max(numbers)
  let avg is mean(numbers)
  return map:
    "total" is total
    "lo" is lo
    "hi" is hi
    "avg" is avg
"""
    result = run_flow(source)
    assert result.last_value == {
        "total": Decimal("60"),
        "lo": Decimal("10"),
        "hi": Decimal("30"),
        "avg": Decimal("20"),
    }
